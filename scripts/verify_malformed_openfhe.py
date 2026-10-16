"""Exercise native serialization failure modes and emit a reproducible report."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from ml.config import PROJECT_ROOT


def invoke(executable: Path, arguments: list[str], environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(executable), *arguments], cwd=PROJECT_ROOT, env=environment, capture_output=True, text=True, timeout=60, check=False)


def main() -> None:
    executable = PROJECT_ROOT / "openfhe" / "day2-build-local" / "fhe_protocol.exe"
    environment = os.environ.copy()
    environment["PATH"] = os.pathsep.join([str(PROJECT_ROOT / "openfhe" / "install" / "lib"), r"C:\msys64\mingw64\bin", environment.get("PATH", "")])
    outcomes: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        public, private, other_public, other_private = root / "public", root / "private", root / "other-public", root / "other-private"
        assert invoke(executable, ["setup", str(public), str(private)], environment).returncode == 0
        assert invoke(executable, ["setup", str(other_public), str(other_private)], environment).returncode == 0
        source = root / "features.csv"
        source.write_text("0,0,0,0,0,0,0\n", encoding="ascii")
        valid = root / "valid"
        assert invoke(executable, ["encrypt", str(public / "context.bin"), str(public / "public-key.bin"), str(source), str(valid)], environment).returncode == 0

        def evaluate_case(name: str, mutate, context: Path | None = None, keys: Path | None = None) -> None:
            request = root / name
            shutil.copytree(valid, request)
            mutate(request)
            process = invoke(executable, ["evaluate", str(context or public / "context.bin"), str(keys or public / "evaluation-mult-keys.bin"), str(request), str(root / f"{name}.ct")], environment)
            outcomes[name] = {
                "exit_code": process.returncode,
                "failed_safely": process.returncode != 0,
                "output_redacted": "secret-key" not in (process.stdout + process.stderr).lower(),
            }

        evaluate_case("corrupted_ciphertext", lambda p: (p / "feature-0.ct").write_bytes(b"corrupt"))
        evaluate_case("truncated_ciphertext", lambda p: (p / "feature-0.ct").write_bytes((p / "feature-0.ct").read_bytes()[:32]))
        evaluate_case("empty_ciphertext", lambda p: (p / "feature-0.ct").write_bytes(b""))
        evaluate_case("random_bytes", lambda p: (p / "feature-0.ct").write_bytes(os.urandom(128)))
        evaluate_case("incompatible_serialization", lambda p: (p / "feature-0.ct").write_text('{"not":"openfhe"}', encoding="utf-8"))
        evaluate_case("wrong_context", lambda _p: None, context=other_public / "context.bin")
        evaluate_case("wrong_evaluation_key", lambda _p: None, keys=other_public / "evaluation-mult-keys.bin")
        evaluate_case("unexpected_slot_count", lambda p: (p / "batch.count").write_text("8193\n", encoding="ascii"))
        wrong_public_request = root / "wrong-public"
        encrypted = invoke(executable, ["encrypt", str(public / "context.bin"), str(other_public / "public-key.bin"), str(source), str(wrong_public_request)], environment)
        mismatched = invoke(executable, ["evaluate", str(public / "context.bin"), str(public / "evaluation-mult-keys.bin"), str(wrong_public_request), str(root / "wrong-public.ct")], environment) if encrypted.returncode == 0 else encrypted
        outcomes["wrong_public_key"] = {"exit_code": mismatched.returncode, "failed_safely": mismatched.returncode != 0, "output_redacted": "secret-key" not in (mismatched.stdout + mismatched.stderr).lower()}

    strict_cases = [name for name in outcomes if name != "wrong_context"]
    passed = all(outcomes[name]["failed_safely"] and outcomes[name]["output_redacted"] for name in strict_cases)
    status = "PARTIAL" if passed and not outcomes["wrong_context"]["failed_safely"] else ("PASS" if passed else "FAIL")
    report = {
        "status": status,
        "timeout_seconds": 60,
        "cases": outcomes,
        "limitation": "A separately generated context with identical CKKS parameters is serialization-compatible; API profile/model checks do not cryptographically bind ciphertexts to a context fingerprint." if status == "PARTIAL" else None,
    }
    destination = PROJECT_ROOT / "benchmarks" / "results" / "malformed_openfhe.json"
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
