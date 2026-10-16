# Benchmarks

## Methodology

The authoritative comparison uses the held-out 6,484-row test split. Normal timing measures `predict_proba` for the full saved batch averaged over 1,000 runs. FHE packs the test rows into CKKS slots and records actual OpenFHE context creation/file parsing, key generation, encryption, evaluation, decryption, and ciphertext-size serialization.

Hardware/OS-specific values should not be generalized to other deployments. The current benchmark artifact does not record peak resident memory, so memory usage is **not measured** rather than estimated.

## Results

| Metric | Normal ML | FHE polynomial ML |
|---|---:|---:|
| Accuracy | 83.2048% | 83.2048% |
| Precision | 70.6918% | 70.6918% |
| Recall | 39.6333% | 39.6333% |
| F1 | 50.7908% | 50.7908% |
| ROC-AUC | 0.83142247 | 0.83142254 |
| Batch inference / total | 0.616959 ms | 2,343.7045 ms |
| Key generation | — | 349.8561 ms |
| Encryption | — | 613.0988 ms |
| Encrypted evaluation | — | 947.4312 ms |
| Decryption | — | 101.5400 ms |
| One input ciphertext | — | 4,195,889 bytes |
| Seven input ciphertexts | — | 29,371,223 bytes |
| Mean FHE/plain-polynomial error | — | `4.71368e-12` |
| Maximum FHE/plain-polynomial error | — | `1.79943e-10` |
| Peak memory | not measured | not measured |

Classification accuracy difference is `0.0` on this split. A direct ratio of total FHE pipeline time to normal model-only batch inference is approximately `3,799×`, but the timings cover different scopes; it should be labeled as an end-to-end research comparison, not an optimized serving benchmark.

## Reproduction

```powershell
.\.venv\Scripts\python.exe -m benchmarks.benchmark
```

The native evaluator and required OpenFHE libraries must already be built. Results are saved under `benchmarks/results/`; never edit measured JSON by hand.

## Interpretation

The experiment demonstrates preserved classification behavior and very small CKKS arithmetic error at substantial latency/ciphertext-size overhead. It does not establish throughput under concurrency, cold-start behavior, peak memory, network transfer cost, or performance on another processor/compiler.
