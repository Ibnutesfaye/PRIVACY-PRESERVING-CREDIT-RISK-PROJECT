# Day 3 FHE ML and Application Report

## Polynomial sigmoid

Observed test logits range from `-5.4622` to `5.5057`, so the approximation interval is `[-6, 6]`. Degree 3, 5, and 7 least-squares Chebyshev fits were compared and converted to the power basis for OpenFHE evaluation.

The selection rule was the lowest degree with maximum grid error no greater than `0.02`. Degree 7 was selected:

```text
p(z) = 0.5
     + 0.2351734039561946 z
     - 0.012339842621857708 z^3
     + 0.0003942635590235865 z^5
     - 0.000004745378487314977 z^7
```

Its maximum approximation error across `[-6,6]` is `0.01450`; mean test probability error is `0.00461`. It preserves the baseline classification metrics. Polynomial output can slightly exceed `[0,1]`, so the client clamps only the decrypted display value while retaining the raw value for research reporting.

## Encrypted test-set evaluation

All 6,484 test records were evaluated genuinely under OpenFHE CKKS. SIMD packing places customer rows in slots and uses seven ciphertexts—one packed ciphertext per feature column.

| Metric | Normal ML | FHE degree-7 model |
| --- | ---: | ---: |
| Accuracy | 0.832048 | 0.832048 |
| Precision | 0.706918 | 0.706918 |
| Recall | 0.396333 | 0.396333 |
| F1 | 0.507908 | 0.507908 |
| ROC-AUC | 0.831422 | 0.831423 |
| Full test-batch inference | 0.617 ms | 947.431 ms evaluation |
| Key generation | — | 349.856 ms |
| Encryption | — | 613.099 ms |
| Decryption | — | 101.540 ms |
| Total FHE pipeline | — | 2,343.705 ms |
| One input ciphertext | — | 4,195,889 bytes |
| Seven input ciphertexts | — | 29,371,223 bytes |

FHE-versus-plaintext-polynomial mean absolute error is `4.71e-12`; maximum absolute error is `1.80e-10`. The encrypted and normal models have zero measured accuracy difference on this split.

## Application architecture

The React interface calls FastAPI `/predict`. For this local academic prototype, FastAPI is a trusted client gateway: it receives form values, applies the training-fitted imputer and scaler, and invokes the OpenFHE executable. The isolated evaluator receives scaled feature ciphertexts and has no secret key.

This means the evaluator is protected from plaintext, but the FastAPI gateway is not. Production browser-side encryption would require an OpenFHE-compatible client runtime and key lifecycle and is explicitly future work.

## API

- `GET /health` reports API and OpenFHE readiness.
- `POST /predict` validates seven fields, performs genuine CKKS inference, and returns the approximate score, prediction, timing, and explicit privacy-boundary facts.
- Request bodies are not logged or persisted by application code.

## Validation

- Full 6,484-record FHE batch completed.
- End-to-end representative API prediction completed.
- React production build and lint completed.
- Browser form submission completed with no console warnings/errors.

