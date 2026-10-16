# Final Research Results

## Main research result

Homomorphic encryption preserved the measured credit-risk classification performance while adding substantial computational and storage overhead.

Across the complete 6,484-record held-out set:

- Normal and FHE accuracy were both 83.2048%.
- Normal and FHE precision were both 70.6918%.
- Normal and FHE recall were both 39.6333%.
- Normal and FHE F1 were both 50.7908%.
- Maximum decrypted CKKS error versus the plaintext polynomial was `1.80e-10`.
- Conventional full-batch inference averaged 0.616959 ms.
- The complete FHE pipeline required 2,343.7045 ms.
- End-to-end FHE overhead was approximately 3,798.8×, adding 2,343.09 ms.
- Encrypted evaluation alone required 947.4312 ms, approximately 1,535.6× conventional batch inference.
- Seven packed input ciphertexts occupied 29,371,223 bytes.

## Interpretation

The experimental evidence supports the hypothesis that OpenFHE CKKS can protect customer features during evaluator-side credit-risk computation without meaningful numerical or classification degradation for this model and test distribution.

The tradeoff is not small. FHE increases latency by several orders of magnitude and produces multi-megabyte ciphertexts. SIMD packing materially improves throughput by sharing that cost across 6,484 customers, but single-request application latency remains measured in seconds.

The word “privacy” applies to the isolated encrypted evaluator. The current React-to-FastAPI segment sends plaintext to a trusted local gateway and is not end-to-end FHE protected.

