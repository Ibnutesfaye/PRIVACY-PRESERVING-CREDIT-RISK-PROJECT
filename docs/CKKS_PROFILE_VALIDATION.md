# CKKS profile validation

The approved pilot profile is `ckks-balanced-degree7-v1`:

- OpenFHE CKKS with its default `HEStd_128_classic` security setting;
- ring dimension 32,768 (selected by OpenFHE for the modulus/depth request);
- multiplicative depth 6;
- 50-bit scaling modulus;
- SIMD capacity 8,192 values;
- seven feature ciphertexts and a degree-7 sigmoid polynomial.

The depth retains one conservative level of headroom around the weighted sum and odd-power polynomial circuit. Reducing depth or ring dimension was not adopted without a separate security and failure-rate study. The goal of this phase is a measured, supportable profile rather than an unverified smaller parameter set.

## Three-run split-process benchmark

All 6,484 held-out samples were packed into each feature ciphertext. Mean times include process startup, deserialization, computation, and serialization:

| Stage | Mean milliseconds |
|---|---:|
| Key/context setup | 1,201.739 |
| Encryption and serialization | 1,651.262 |
| Evaluation and serialization | 2,596.587 |
| Decryption and deserialization | 632.682 |
| Total including fresh setup | 6,082.270 |

Fresh key setup is not required for every prediction and can be amortized over a key/profile lifetime. The evaluator boundary is slower than the earlier in-memory research benchmark because the enterprise measurement includes ciphertext transport serialization and independent process startup.

Serialized sizes were 4,195,845 bytes for the public key, 17,305,585 bytes for multiplication evaluation keys, 29,374,863 bytes for the seven-ciphertext request, 1,050,085 bytes for the result, and 2,098,401 bytes for the client-only secret key.

## Accuracy and numerical equivalence

The split protocol retained exactly the conventional threshold metrics: 83.2048% accuracy, 70.6918% precision, 39.6333% recall, and 50.7908% F1. There were zero classification differences across 6,484 samples. Compared with the exact sigmoid, the polynomial/FHE score mean absolute error was 0.004614 and the maximum was 0.008077. These values include intentional polynomial approximation as well as negligible CKKS numerical error.

The machine-readable evidence is in `benchmarks/results/split_protocol.json`.
