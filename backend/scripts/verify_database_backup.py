"""Validate a backup checksum; restoration remains an explicit operator procedure."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup", type=Path)
    arguments = parser.parse_args()
    backup = arguments.backup.resolve()
    sidecar = backup.with_suffix(backup.suffix + ".sha256")
    expected = sidecar.read_text(encoding="ascii").split()[0]
    actual = hashlib.sha256(backup.read_bytes()).hexdigest()
    if actual != expected:
        raise RuntimeError("Backup checksum validation failed")
    print(f"PASS: checksum verified for {backup.name}")


if __name__ == "__main__":
    main()
