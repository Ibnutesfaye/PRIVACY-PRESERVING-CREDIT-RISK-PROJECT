# Final Demonstration Script — 7 Minutes

## Before the presentation

Open two PowerShell terminals at the project root.

Terminal 1 — API:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Terminal 2 — React:

```powershell
cd frontend
npm.cmd run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173`. Confirm `http://127.0.0.1:8000/health` returns `{"status":"ok","openfhe":"ready"}`. Keep these files ready:

- `docs/reports/day3_report.md`
- `benchmarks/results/comparison.json`
- `openfhe/src/day3_fhe_predict.cpp`
- `docs/threat-model.md`

## 0:00–0:45 — The problem

Say:

> Banks and lenders use customer information to estimate credit risk. In a conventional remote system, the computation server receives sensitive values such as income, loan amount, interest rate, and credit history in plaintext. TLS protects transmission, but the server normally decrypts the data before computing. This project asks whether the evaluator can calculate a useful prediction without seeing those feature values.

Show the React page title and form.

## 0:45–1:25 — Normal machine learning

Say:

> I first built a normal logistic-regression baseline using the actual 32,581-row dataset. After removing 165 exact duplicates, I used seven numerical features. Imputation and standardization were fitted only on training data. The model calculates a weighted sum, z equals w dot x plus b, then applies a sigmoid.

Show:

```text
Customer data -> preprocessing -> logistic regression -> risk score
```

State the baseline:

- Accuracy: 83.20%
- Precision: 70.69%
- Recall: 39.63%
- F1: 50.79%
- ROC-AUC: 0.8314

Mention honestly that recall is a model limitation.

## 1:25–2:10 — Privacy problem and FHE solution

Say:

> In the conventional architecture, the evaluator sees the scaled feature vector. With OpenFHE CKKS, the trusted client encodes and encrypts those real values. The evaluator receives ciphertext, multiplies encrypted features by plaintext model weights, adds the bias, and evaluates a polynomial probability approximation. It returns an encrypted result. Only the client boundary has the secret key and decrypts.

Show:

```text
Customer -> preprocess -> CKKS encrypt -> ciphertext evaluator
         -> encrypted weighted sum -> encrypted polynomial
         -> encrypted result -> client decrypts -> risk score
```

Clarify:

> The production API contract receives seven serialized ciphertexts and returns only a result ciphertext. For this demo, a separate trusted native client performs preprocessing, encryption, and decryption. The React browser itself is not an audited OpenFHE client; the old plaintext form is compatibility-only and disabled in production.

## 2:10–2:55 — FHE-friendly sigmoid

Say:

> The exact sigmoid contains exponentiation and division, which are inconvenient in this leveled arithmetic circuit. I measured every test logit; the range was approximately minus 5.46 to plus 5.51. I tested degree 3, 5, and 7 Chebyshev fits on minus 6 to plus 6. Degree 7 was the lowest candidate with maximum interval error below 0.02.

Show the polynomial:

```text
p(z) = 0.5 + 0.2351734z - 0.0123398z³
             + 0.000394264z⁵ - 0.00000474538z⁷
```

State maximum approximation error: 0.01450.

## 2:55–4:10 — Live encrypted prediction

Use the default form values:

- Age: 28
- Income: 45,000
- Employment: 5
- Loan: 10,000
- Interest: 11.5
- Loan/income: 0.22
- Credit history: 4

Click **Predict securely**.

While waiting, say:

> The trusted client applies training-fitted preprocessing, creates and owns keys, and serializes seven ciphertexts. FastAPI invokes only `fhe_protocol evaluate` with context, evaluation keys, and ciphertext paths. It returns the encrypted polynomial result; the trusted client decrypts it with a private-key path never supplied to the server.

Expected result is approximately:

```text
Risk score: 27.1%
Prediction: LOW RISK
```

Timing varies because CKKS encryption is randomized and the machine load changes. Demonstrate the encryption, evaluation, decryption, and total timing cards.

## 4:10–5:05 — Show genuine OpenFHE computation

Open `openfhe/src/day3_fhe_predict.cpp` and point to:

- `CreateContext`
- `KeyGen` and `EvalMultKeyGen`
- `ClientEncryptColumns`
- `ServerEncryptedLogit`
- `ServerPolynomialSigmoid`
- client `Decrypt`

Say:

> This is genuine OpenFHE C++, not a Python mock. For the complete test experiment, I packed 6,484 customers into CKKS slots across seven feature-column ciphertexts.

## 5:05–6:10 — Research result and overhead

Show the comparison table:

| Metric | Normal | FHE |
| --- | ---: | ---: |
| Accuracy | 83.2048% | 83.2048% |
| Precision | 70.6918% | 70.6918% |
| Recall | 39.6333% | 39.6333% |
| F1 | 50.7908% | 50.7908% |
| Normal batch / encrypted evaluation | 0.617 ms | 947.431 ms |
| Total FHE pipeline | — | 2,343.705 ms |
| Seven ciphertexts | — | 29.37 MB |

Say:

> The main result is that encrypted inference preserved measured accuracy. The maximum FHE numerical difference from the plaintext polynomial was 1.8 times 10 to the minus 10. The cost was substantial: the full FHE batch pipeline was approximately 3,799 times slower than normal batch inference and added about 2.343 seconds. SIMD packing amortizes this across 6,484 customers, but individual online requests still pay fixed cryptographic costs.

## 6:10–6:50 — Security and limitations

Say:

> FHE protects feature confidentiality during the isolated encrypted computation. It does not automatically provide TLS, authentication, authorization, model confidentiality, output privacy, integrity, availability, or secure key management. The evaluator can still observe ciphertext size and timing. A production design must move encryption to a customer-controlled client, use TLS, isolate services, manage keys securely, authenticate users, limit requests, and protect software dependencies.

## 6:50–7:15 — Conclusion

Say:

> The research hypothesis is supported. OpenFHE CKKS can perform this credit-risk inference without exposing plaintext customer features to the evaluator and without measured accuracy loss on the test set. The tradeoff is much higher computation, storage, and system complexity. FHE strengthens confidentiality during computation, but it is one layer in a complete security architecture.

## Questions you should be ready to answer

### Why CKKS instead of BFV or BGV?

The model uses standardized real-valued features, real coefficients, and polynomial probabilities. CKKS natively supports approximate packed real arithmetic.

### Why logistic regression?

Its central operation is a linear weighted sum, which maps efficiently to additions and ciphertext-by-plaintext multiplications. It is interpretable and appropriate for a first FHE research prototype.

### Why is the FHE accuracy identical?

The polynomial preserves the 0.5 decision boundary for this test distribution, and CKKS numerical error is far smaller than the margins required to change a tested class decision.

### Is the whole application private?

The versioned evaluator API is ciphertext-only and cannot decrypt the result. The React compatibility form still sends plaintext to a legacy development endpoint, so production disables that route and uses a separate trusted client.

### What if the sigmoid polynomial produces a value outside 0–1?

The raw research value is retained. The trusted client clamps only the displayed score after decryption. Future work could select a different approximation or interval.

### What is the biggest weakness?

Class-1 recall is only 39.63%; browser-side key custody/encryption is not implemented; and split-process evaluation takes seconds with roughly 29.4 MB request ciphertexts. Docker/k6 target acceptance, fairness/calibration, MFA/SSO, shared queues/rate limits, and HSM/KMS integration remain gates.

## Demo fallback

If a live request is slow or interrupted, do not invent a result. Show the previously measured files:

- `benchmarks/results/comparison.json`
- `benchmarks/results/fhe_timing.json`
- `docs/reports/day3_report.md`

Explain that these files were generated by successful local executions and are covered by automated result-contract tests.
