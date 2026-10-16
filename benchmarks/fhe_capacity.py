"""Repeated native CKKS capacity measurements for workstation evidence only."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
from time import perf_counter

import numpy as np

from ml.config import PROCESSED_DIR, PROJECT_ROOT


class MemoryStatus(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong), ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong), ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong), ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong), ("available_extended_virtual", ctypes.c_ulonglong)]


def timed(command: list[str], environment: dict[str, str]) -> float:
    started = perf_counter()
    result = subprocess.run(command, cwd=PROJECT_ROOT, env=environment, capture_output=True, text=True, timeout=120, check=False)
    elapsed = (perf_counter() - started) * 1000
    if result.returncode != 0:
        raise RuntimeError("OpenFHE capacity stage failed")
    return elapsed


def summary(values: list[float]) -> dict[str, float]:
    data = np.asarray(values)
    return {name: float(value) for name, value in {
        "mean": data.mean(), "median": np.median(data), "p95": np.percentile(data, 95),
        "p99": np.percentile(data, 99), "min": data.min(), "max": data.max(), "stddev": data.std(),
    }.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--batches", default="1,64,247")
    arguments = parser.parse_args()
    if not 3 <= arguments.runs <= 20:
        raise ValueError("runs must be between 3 and 20")
    batches = [int(value) for value in arguments.batches.split(",")]
    if any(value < 1 or value > 8192 for value in batches):
        raise ValueError("batch sizes must be between 1 and 8192")

    executable = PROJECT_ROOT / "openfhe" / "day2-build-local" / "fhe_protocol.exe"
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join([str(PROJECT_ROOT / "openfhe" / "install" / "lib"), r"C:\msys64\mingw64\bin", environment.get("PATH", "")])
    features = np.load(PROCESSED_DIR / "train_test_data.npz", allow_pickle=False)["X_test"]
    results: dict[str, object] = {}
    profile: dict[str, object] | None = None
    for batch in batches:
        stages: dict[str, list[float]] = {name: [] for name in ("key_generation", "encryption_serialization", "encrypted_evaluation_serialization", "decryption_deserialization", "total")}
        sizes: dict[str, int] = {}
        for _ in range(arguments.runs):
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                public, private, request = root / "public", root / "private", root / "request"
                source, response, scores = root / "features.csv", root / "result.ct", root / "scores.txt"
                np.savetxt(source, features[:batch], delimiter=",", fmt="%.17g")
                key_ms = timed([str(executable), "setup", str(public), str(private)], environment)
                encryption_ms = timed([str(executable), "encrypt", str(public / "context.bin"), str(public / "public-key.bin"), str(source), str(request)], environment)
                evaluation_ms = timed([str(executable), "evaluate", str(public / "context.bin"), str(public / "evaluation-mult-keys.bin"), str(request), str(response)], environment)
                decryption_ms = timed([str(executable), "decrypt", str(public / "context.bin"), str(private / "secret-key.bin"), str(response), str(batch), str(scores)], environment)
                for name, value in (("key_generation", key_ms), ("encryption_serialization", encryption_ms), ("encrypted_evaluation_serialization", evaluation_ms), ("decryption_deserialization", decryption_ms)):
                    stages[name].append(value)
                stages["total"].append(key_ms + encryption_ms + evaluation_ms + decryption_ms)
                sizes = {"request_bytes": sum(path.stat().st_size for path in request.glob("*.ct")), "response_bytes": response.stat().st_size}
                profile = json.loads((public / "profile.json").read_text(encoding="utf-8"))
        results[str(batch)] = {"runs": arguments.runs, "timing_ms": {name: summary(values) for name, values in stages.items()}, "serialized_sizes": sizes}

    memory = MemoryStatus()
    memory.length = ctypes.sizeof(MemoryStatus)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
    report = {
        "scope": "workstation measurement; not a production SLA",
        "hardware": {"processor": platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "unknown"), "logical_cpu_count": os.cpu_count(), "ram_bytes": memory.total_physical, "os": platform.platform()},
        "openfhe_profile": profile,
        "batch_results": results,
    }
    destination = PROJECT_ROOT / "benchmarks" / "results" / "fhe_capacity.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

