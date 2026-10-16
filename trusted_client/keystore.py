from __future__ import annotations

from pathlib import Path
from typing import Protocol


class KeyStore(Protocol):
    """Boundary implemented by a pilot local store or a future HSM/KMS adapter."""

    def secret_key_path(self) -> Path: ...


class LocalDirectoryKeyStore:
    """Pilot-only store; relies on institutional OS ACLs and encrypted storage."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory.resolve()

    def secret_key_path(self) -> Path:
        key = self.directory / "secret-key.bin"
        if not key.is_file():
            raise FileNotFoundError("The client secret key is unavailable")
        return key

