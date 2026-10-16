from __future__ import annotations

import argparse
import getpass
from pathlib import Path

from ml.config import PROJECT_ROOT
from trusted_client.client import TrustedClient, load_applicants
from trusted_client.keystore import LocalDirectoryKeyStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Trusted local encrypted-inference client")
    commands = parser.add_subparsers(dest="command", required=True)
    initialize = commands.add_parser("init-keys", help="Generate a client key pair and evaluator bundle")
    initialize.add_argument("--public-bundle", type=Path, required=True)
    initialize.add_argument("--key-dir", type=Path, required=True)
    predict = commands.add_parser("predict", help="Preprocess, encrypt, submit, and decrypt locally")
    predict.add_argument("--input", type=Path, required=True)
    predict.add_argument("--public-bundle", type=Path, required=True)
    predict.add_argument("--key-dir", type=Path, required=True)
    predict.add_argument("--api-url", required=True)
    arguments = parser.parse_args()
    executable = PROJECT_ROOT / "openfhe" / "day2-build-local" / "fhe_protocol.exe"
    if arguments.command == "init-keys":
        client = TrustedClient(executable, arguments.public_bundle, LocalDirectoryKeyStore(arguments.key_dir))
        arguments.public_bundle.mkdir(parents=True, exist_ok=True)
        arguments.key_dir.mkdir(parents=True, exist_ok=True)
        client._native(["setup", str(arguments.public_bundle), str(arguments.key_dir)])
        print("Key generation complete. Provision only the public bundle to the evaluator operator.")
        return
    token = getpass.getpass("Administrator access token (masked): ")
    client = TrustedClient(executable, arguments.public_bundle, LocalDirectoryKeyStore(arguments.key_dir))
    result = client.predict(load_applicants(arguments.input), arguments.api_url, token)
    print(f"Prediction ID: {result['prediction_id']}")
    for index, score in enumerate(result["scores"], start=1):
        print(f"Applicant {index}: score={score:.8f}")


if __name__ == "__main__":
    main()

