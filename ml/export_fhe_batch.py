"""Export scaled Day 1 test features for packed OpenFHE evaluation."""

from __future__ import annotations

import numpy as np

from ml.config import PROCESSED_DIR, PROJECT_ROOT


def main() -> None:
    data = np.load(PROCESSED_DIR / "train_test_data.npz")
    output_dir = PROJECT_ROOT / "openfhe" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)
    np.savetxt(output_dir / "fhe_test_batch.csv", data["X_test"], delimiter=",", fmt="%.17g")
    np.savetxt(output_dir / "fhe_test_targets.csv", data["y_test"], delimiter=",", fmt="%d")
    print(f"Exported {len(data['X_test'])} scaled test rows for packed CKKS evaluation")


if __name__ == "__main__":
    main()

