"""Create a PostgreSQL custom-format backup without placing credentials in arguments."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import re

from sqlalchemy.engine import make_url

from backend.app.database import database_url


def postgres_tool(name: str) -> str:
    discovered = shutil.which(name)
    if discovered:
        return discovered
    root = Path(r"C:\Program Files\PostgreSQL")
    if root.is_dir():
        versions = sorted((item for item in root.iterdir() if item.is_dir()), key=lambda item: tuple(int(part) for part in item.name.split(".") if part.isdigit()), reverse=True)
        for version in versions:
            candidate = version / "bin" / f"{name}.exe"
            if candidate.is_file():
                return str(candidate)
    raise RuntimeError(f"{name} was not found")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    target = arguments.destination.resolve()
    if target.suffix.casefold() not in {".dump", ".backup"}:
        raise ValueError("Backup destination must end in .dump or .backup")
    target.parent.mkdir(parents=True, exist_ok=True)
    url = make_url(database_url())
    if not url.drivername.startswith("postgresql") or not url.database:
        raise RuntimeError("Backup supports PostgreSQL only")
    environment = os.environ.copy()
    environment["PGPASSWORD"] = url.password or ""
    command = [postgres_tool("pg_dump"), "--host", url.host or "127.0.0.1", "--port", str(url.port or 5432), "--username", url.username or "", "--dbname", url.database, "--format=custom", "--no-owner", "--no-privileges", "--file", str(target)]
    completed = subprocess.run(command, env=environment, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        target.unlink(missing_ok=True)
        diagnostic = (completed.stderr or completed.stdout or "No diagnostic output").strip()
        if url.password:
            diagnostic = diagnostic.replace(url.password, "[REDACTED]")
        diagnostic = re.sub(r"(?i)(postgres(?:ql)?(?:\+\w+)?://)[^\s@]+@", r"\1[REDACTED]@", diagnostic)
        raise RuntimeError(f"PostgreSQL backup failed with exit code {completed.returncode}: {diagnostic}")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(target.suffix + ".sha256").write_text(f"{digest}  {target.name}\n", encoding="ascii")
    print(f"PASS: backup created at {target} with SHA-256 sidecar")


if __name__ == "__main__":
    main()
