# Privacy-Preserving Credit Risk Prediction Using Homomorphic Encryption with OpenFHE

## Abstract

Credit-risk inference normally requires a computation service to receive customer financial attributes in plaintext. This project investigates whether a logistic-regression risk model can be evaluated while an isolated computation server receives only encrypted features. A conventional Python baseline was trained on a supplied 32,581-row dataset using seven numerical features. Its weighted sum was translated to OpenFHE C++ and evaluated with the CKKS approximate-arithmetic scheme. Because the exact sigmoid is unsuitable for the selected low-depth arithmetic circuit, degree-3, degree-5, and degree-7 polynomial approximations were compared over the complete measured logit range. A degree-7 polynomial was selected and evaluated over all 6,484 test samples packed into CKKS slots.

The conventional and encrypted models both obtained 83.2048% accuracy, 70.6918% precision, 39.6333% recall, and 50.7908% F1 at threshold 0.5. The maximum error between decrypted FHE scores and the equivalent plaintext polynomial was `1.80e-10`. Conventional inference over the full test batch averaged 0.617 ms, while the measured FHE pipeline required 2,343.705 ms, approximately 3,798.8 times longer end to end. Seven packed feature ciphertexts occupied about 29.4 MB. The results show that privacy-preserving encrypted evaluation is feasible with negligible numerical and classification impact, but incurs substantial computation and storage overhead. The prototype protects feature confidentiality only inside the isolated evaluator; its FastAPI gateway remains trusted and receives plaintext browser input.

## Chapter 1 — Introduction

### 1.1 Context

Credit-risk models use personal and financial information to estimate the likelihood of default or another adverse outcome. A conventional remote prediction architecture sends customer attributes to an application or inference server, where preprocessing and model evaluation occur in plaintext. Transport encryption protects values while moving across a network, but values are normally decrypted before computation. This creates an exposure point at the computation service.

Homomorphic encryption offers a different property: selected operations can be performed directly on ciphertext. An evaluator can transform an encrypted input into an encrypted result without receiving the decryption key. This property is attractive where organizations want to reduce trust in a computation service or isolate sensitive processing.

### 1.2 Problem statement

The project asks whether credit-risk prediction can be performed over encrypted customer features using OpenFHE while retaining practically identical results to a conventional model. It also asks how much computational and storage overhead this privacy property introduces.

### 1.3 Research questions

- RQ1: Can credit-risk prediction be performed on encrypted customer features using OpenFHE?
- RQ2: How much accuracy difference exists between normal and FHE inference?
- RQ3: What computational overhead does homomorphic encryption introduce?
- RQ4: How does polynomial sigmoid approximation affect prediction accuracy?
- RQ5: How does ciphertext computation compare with plaintext computation in latency and storage?

### 1.4 Hypothesis

Homomorphic encryption can enable privacy-preserving credit-risk inference without exposing plaintext customer features to the evaluator, but it introduces additional computation and storage overhead compared with conventional inference.

### 1.5 Contributions

The work provides a reproducible dataset analysis, conventional baseline, extracted mathematical model, genuine OpenFHE CKKS implementation, polynomial study, full encrypted test-set evaluation, numerical verification, performance benchmark, application prototype, automated tests, and explicit threat model.

## Chapter 2 — Background

### 2.1 Credit risk and binary classification

The supplied target `loan_status` is binary: class 0 represents the lower-risk/non-default class and class 1 represents the higher-risk/default class. A probabilistic classifier assigns a score that can be thresholded to form a class decision. Accuracy alone is inadequate when the classes are imbalanced, so precision, recall, F1, ROC-AUC, and a confusion matrix are also reported.

### 2.2 Logistic regression

Logistic regression computes a linear logit:

```text
z = w1x1 + w2x2 + ... + wnxn + b
```

and maps it to a probability using:

```text
sigmoid(z) = 1 / (1 + exp(-z))
```

Its linear structure is well suited to arithmetic circuits because the weighted sum requires additions and multiplications by known plaintext coefficients. The exact sigmoid introduces exponentiation and division, which are inconvenient for a compact leveled-FHE circuit.

### 2.3 Homomorphic encryption

Homomorphic encryption supports computation on encrypted messages. A client generates keys, encodes and encrypts inputs, and sends ciphertext to an evaluator. The evaluator applies supported operations and returns ciphertext. The client decrypts the result. Security depends on scheme assumptions, parameters, implementation, key handling, and the surrounding application.

### 2.4 Fully homomorphic encryption

FHE supports general arithmetic circuits subject to practical resource and parameter constraints. Multiplicative operations consume levels and increase noise or approximation error. Bootstrapping can refresh ciphertexts for deeper computation but is expensive and unnecessary for this fixed low-depth project circuit.

### 2.5 CKKS

CKKS, introduced by Cheon, Kim, Kim, and Song, supports approximate arithmetic over packed real or complex values. Approximation is intentional: scale management and encryption noise affect lower-order precision. This matches machine-learning inference where features and coefficients are real-valued and small numerical error can be measured and tolerated. The original scheme is described in [Homomorphic Encryption for Arithmetic of Approximate Numbers](https://eprint.iacr.org/2016/421.pdf).

### 2.6 OpenFHE

OpenFHE is an open-source library implementing CKKS and other homomorphic-encryption schemes. It provides context and parameter generation, keys, encoding, encryption, homomorphic operations, decryption, serialization, packing, and automatic maintenance operations. Its design and relationship to earlier libraries are described by Al Badawi et al. in [OpenFHE: Open-Source Fully Homomorphic Encryption Library](https://eprint.iacr.org/2022/915.pdf). This project pins OpenFHE v1.5.1 and uses its official C++ API.

## Chapter 3 — Related Work

Approximate homomorphic arithmetic was developed to make real- and complex-number workloads practical under encryption. CKKS encodes vectors into polynomial-ring elements and treats bounded approximation error as part of the computation. Subsequent work has improved RNS implementations, bootstrapping, precision, and performance.

OpenFHE consolidates several scheme families and exposes a common software architecture with automatic and compiler-friendly modes. It is appropriate for this project because it supports CKKS packing, real-number encoding, ciphertext-by-plaintext multiplication, ciphertext multiplication, evaluation keys, serialization, and parameter selection in a maintained open-source implementation.

Privacy-preserving machine learning commonly adapts models to arithmetic-circuit constraints. Linear and logistic models are natural starting points because their dominant operation is a dot product. Non-polynomial activations are replaced by low-degree approximations selected for a bounded input interval. This project follows that approach but evaluates approximation choice empirically on its own measured logit distribution rather than assuming arbitrary coefficients.

Security parameters for HE must be selected with reference to reviewed guidance. The [Homomorphic Encryption Security Guidelines](https://homomorphicencryption.org/security-guidelines/) describe community guidance and clarify that the 2018 document is security guidance rather than a formal interoperability standard. This prototype lets OpenFHE select the ring dimension for the configured depth, scaling size, and batch size rather than manually claiming an unsupported security level.

The contribution here is not a new cryptographic scheme. It is an experimentally honest integration and measurement of a credit-risk pipeline, including a separated evaluator boundary and application demonstration.

## Chapter 4 — Methodology

### 4.1 Dataset inspection

The actual supplied CSV was inspected before training. It contains 32,581 rows and 12 columns. Missing values occur in `person_emp_length` (895) and `loan_int_rate` (3,116). There are 165 exact duplicate rows. The target distribution is 25,473 class-0 records and 7,108 class-1 records. Numerical ranges and IQR outlier counts were recorded. Five ages are outside 18–100, with a maximum of 144; employment length reaches 123.

### 4.2 Feature selection

Seven numerical features were selected to create a tractable first FHE circuit: age, income, employment length, loan amount, interest rate, loan-to-income ratio, and credit-history length. Categorical values remain relevant future work. `loan_grade` was excluded partly because it may represent a prior underwriting judgment closely related to the outcome.

### 4.3 Preprocessing

Exact full-row duplicates were removed before feature selection, leaving 32,416 records. A stratified 80/20 split with random seed 42 produced 25,932 training and 6,484 test records. Median imputation and standardization were fitted only on training data. Saved artifacts ensure the same transformation is applied during API and FHE inference.

### 4.4 Baseline training

Scikit-learn logistic regression was trained with a maximum of 2,000 iterations. The model, imputer, scaler, feature ordering, and metadata were serialized. Predictions were evaluated using accuracy, precision, recall, F1, ROC-AUC, and a confusion matrix.

### 4.5 Mathematical extraction

The seven coefficients and intercept were exported. A manual NumPy dot product and sigmoid were compared against scikit-learn over every test record. Both logit and probability maximum absolute errors were 0.0, validating the extracted form used by C++.

### 4.6 Polynomial selection

Test logits ranged from `-5.4622` to `5.5057`. A symmetric `[-6,6]` interval covers the complete measured test distribution. Least-squares Chebyshev fits of degrees 3, 5, and 7 were generated over a 20,001-point grid and converted to power coefficients. The selection rule was the lowest degree with maximum grid error at most 0.02. Degree 7 met this rule; degrees 3 and 5 did not.

### 4.7 FHE experiment

OpenFHE CKKS encrypted seven feature columns, each containing all 6,484 test customers in SIMD slots. The evaluator calculated an encrypted weighted sum and the odd degree-7 polynomial using powers `z²`, `z³`, `z⁵`, and `z⁷`. The client decrypted all slots. Classification metrics were computed from actual decrypted FHE scores, not simulated values.

### 4.8 Timing method

Conventional `predict_proba` over the complete test matrix was repeated 1,000 times and averaged. FHE phase timings were measured in C++ with a steady clock. Total FHE latency includes input parsing/context creation, key generation, encryption, ciphertext-size serialization, evaluation, and decryption. Because these definitions differ, the report presents individual FHE phases as well as total latency.

## Chapter 5 — System Design

### 5.1 Components

- Python ML pipeline: inspection, preprocessing, training, parameter export, polynomial analysis, and metric aggregation.
- C++ OpenFHE layer: CKKS context, keys, encoding, encryption, encrypted linear inference, polynomial inference, decryption, and serialization measurement.
- FastAPI gateway: validation, saved preprocessing, subprocess orchestration, and response schema.
- React frontend: seven input fields, encrypted-inference action, result, timing, and privacy disclosure.

### 5.2 Cryptographic boundary

The evaluator receives ciphertext and plaintext model parameters. Its evaluation functions have no secret-key parameter. The trusted client boundary retains the secret key and decrypts results. Public and evaluation keys may be supplied for supported operations without enabling ordinary decryption.

### 5.3 Prototype application boundary

The browser does not implement OpenFHE. It sends plaintext values to a trusted local FastAPI gateway. The gateway performs preprocessing and invokes the C++ process, which creates keys and encryption before calling its isolated evaluator functions. Therefore the prototype proves ciphertext-only evaluator computation but not browser-to-evaluator end-to-end encryption.

## Chapter 6 — Implementation

### 6.1 Conventional pipeline

Pandas loads the dataset; NumPy stores train/test arrays; scikit-learn performs imputation, scaling, logistic regression, and metrics; joblib stores artifacts; Matplotlib and Seaborn generate plots. Fixed seeds and saved metadata support reproducibility.

### 6.2 CKKS context and keys

The basic weighted-sum circuit uses multiplicative depth 1. The polynomial batch circuit uses configured depth 6, scaling-modulus size 50, and batch size 8,192. OpenFHE selected ring dimension 32,768 for the deeper packed circuit. Public and secret keys are generated per executable invocation, along with a multiplication evaluation key.

### 6.3 Encrypted weighted sum

Each encrypted feature is multiplied by a plaintext coefficient. Weighted ciphertexts are added and the plaintext intercept is added. Day 2 verified a representative logit with absolute error around `1.14e-13`.

### 6.4 Encrypted polynomial

The selected polynomial is:

```text
p(z) = 0.5 + 0.2351734039561946z
             - 0.012339842621857708z³
             + 0.0003942635590235865z⁵
             - 0.000004745378487314977z⁷
```

The circuit reuses powers to control depth. Tiny even coefficients caused by numerical fitting were zeroed because `sigmoid(z)-0.5` is odd over a symmetric interval.

### 6.5 API and frontend

`GET /health` reports readiness. `POST /predict` validates input ranges, applies saved preprocessing, writes a temporary scaled vector, runs the OpenFHE executable, reads the decrypted score and timing, and removes temporary files. Application code does not log or persist request bodies. The React UI reports the approximate score, risk class, phase timings, and explicit boundary disclosure.

## Chapter 7 — Experiments

### 7.1 Baseline experiment

The normal model was evaluated on 6,484 held-out records. Its confusion matrix was `[[4833,233],[856,562]]`. Class imbalance helps explain why accuracy is stronger than recall for class 1.

### 7.2 Approximation experiment

Degree 3 produced grid maximum error 0.08174 and test mean absolute probability error 0.03459. Degree 5 produced grid maximum error 0.03499 and test MAE 0.01245. Degree 7 produced grid maximum error 0.01450 and test MAE 0.00461. All retained the same threshold-based classification metrics on this split, but degree 7 satisfied the declared approximation criterion.

### 7.3 Encrypted numerical experiment

All 6,484 test samples were encrypted and evaluated in one packed run. FHE scores were compared against plaintext degree-7 scores. Mean absolute error was `4.71e-12`; maximum absolute error was `1.80e-10`.

### 7.4 Application experiment

A representative profile—age 28, income 45,000, employment length 5, loan amount 10,000, interest rate 11.5, loan-to-income ratio 0.22, and credit history 4—returned an approximate score near 0.2714 and `LOW RISK`. Live browser submission completed with no console warnings or errors.

### 7.5 Validation experiment

Seventeen automated tests include 14 data, model, FHE, API, and invalid-input checks plus three final documentation-contract checks. Negative income, negative loan amount, age zero, missing required income, and extreme out-of-domain values are rejected with HTTP 422. Missing nullable employment length and interest rate use training-fitted medians.

## Chapter 8 — Results

### 8.1 Predictive results

| Metric | Normal ML | FHE polynomial ML |
| --- | ---: | ---: |
| Accuracy | 0.832048 | 0.832048 |
| Precision | 0.706918 | 0.706918 |
| Recall | 0.396333 | 0.396333 |
| F1 | 0.507908 | 0.507908 |
| ROC-AUC | 0.831422 | 0.831423 |

There was no measured accuracy, precision, recall, or F1 loss. The tiny ROC-AUC difference is consistent with approximate numerical perturbation.

### 8.2 Performance results

| Measurement | Result |
| --- | ---: |
| Conventional 6,484-sample batch | 0.616959 ms |
| FHE key generation | 349.8561 ms |
| FHE encryption | 613.0988 ms |
| FHE evaluation | 947.4312 ms |
| FHE decryption | 101.5400 ms |
| Complete FHE pipeline | 2,343.7045 ms |
| One packed input ciphertext | 4,195,889 bytes |
| Seven packed input ciphertexts | 29,371,223 bytes |

The complete FHE pipeline was about 3,798.8 times slower than conventional full-batch inference and added about 2,343.09 ms. FHE evaluation alone was about 1,535.6 times the conventional batch inference time. SIMD amortizes the complete pipeline to about 0.3615 ms per packed customer, but a single online request still pays the fixed cryptographic costs and measured approximately 2.4–3.4 seconds during application tests.

### 8.3 Answers to research questions

- RQ1: Yes. The trained linear model and polynomial approximation were evaluated over real OpenFHE CKKS ciphertext.
- RQ2: The measured accuracy difference was 0.0 on the saved test set.
- RQ3: End-to-end batch latency increased by approximately 3,798.8 times, with about 2.343 seconds additional latency.
- RQ4: Degree 7 reduced test mean probability error to 0.00461 and preserved threshold metrics. Lower degrees preserved classification here but failed the declared maximum interval-error criterion.
- RQ5: FHE evaluation required 947.4 ms versus 0.617 ms conventional batch inference, and seven input ciphertexts occupied approximately 29.4 MB.

### 8.4 Hypothesis assessment

The evidence supports the hypothesis. Customer features remained encrypted during the isolated computation and prediction accuracy was preserved, while computation and storage overhead increased substantially.

## Chapter 9 — Security Analysis

### 9.1 Protected property

The evaluator cannot normally decrypt feature ciphertexts, intermediate logits, polynomial terms, or the encrypted result because it does not receive the secret key. This demonstrates confidentiality during evaluator computation under the scheme and threat assumptions.

### 9.2 Non-protected properties

FHE does not protect network traffic, authenticate participants, authorize users, hide plaintext model parameters, prevent metadata leakage, guarantee output integrity, stop denial of service, or repair application vulnerabilities. The browser-to-FastAPI path is plaintext inside local HTTP in the prototype. TLS and a customer-controlled encryption client are required for a stronger deployment boundary.

### 9.3 Key management

Secret keys are generated per invocation and remain in process memory; they are not serialized. This reduces persistent-key exposure but is not a production key-management design. Production requires a defined lifecycle, memory protection, rotation, revocation, backup policy, and potentially hardware-backed storage.

### 9.4 Malicious behavior and side channels

The evaluator is modeled as honest-but-curious. A malicious evaluator could return crafted results, deviate from the model, or exploit protocol behavior. Timing, ciphertext size, request frequency, and outputs can reveal metadata. Host compromise can expose gateway plaintext and key memory. These threats require controls beyond FHE.

The complete threat model is in `docs/threat-model.md`.

## Chapter 10 — Limitations

The prototype uses only numerical features and an unweighted logistic model. Higher-risk recall is modest. Categorical features could improve prediction but expand the circuit. The evaluator knows model parameters. The polynomial is validated on the observed range and can overshoot `[0,1]`. The application gateway is trusted and sees plaintext. Benchmark results come from one machine and one primary packed run; repeated trials and confidence intervals are not reported. Memory usage is not fully profiled. No authentication, production TLS, database, bootstrapping, malicious-server verification, or production key service is included.

The phrase “privacy-preserving prediction” refers specifically to encrypted evaluator computation, not a claim that the entire application is private or secure.

## Chapter 11 — Future Work

Future research should move encryption/decryption to a customer-controlled client, separate gateway and evaluator hosts, serialize ciphertext transport, and add TLS and authentication. Prediction research should evaluate categorical encoding, threshold tuning, class weights, calibration, and fairness. Cryptographic research should compare polynomial bases, optimized evaluation schedules, alternative intervals, repeated performance trials, memory use, and hardware acceleration. Model confidentiality could be investigated using protected weights or multi-party protocols. Integrity could be strengthened with authenticated or verifiable computation. Operational work should add key lifecycle management, quotas, audit controls, monitoring, dependency scanning, and privacy-impact review.

## Chapter 12 — Conclusion

This project demonstrates that a conventional credit-risk logistic-regression model can be adapted to genuine OpenFHE CKKS inference. A degree-7 polynomial replaced the exact sigmoid after an empirical approximation study. All 6,484 held-out customers were evaluated in packed ciphertext, producing negligible numerical error and no measured loss in threshold-based classification performance.

The privacy benefit has a clear price: roughly 3,799 times end-to-end batch latency and approximately 29.4 MB for seven packed input ciphertexts. This tradeoff is the central result. FHE can reduce plaintext exposure at the evaluator, but it does not replace TLS, authentication, authorization, endpoint security, secure key management, integrity controls, or careful application design. The resulting system is a reproducible research prototype and a foundation for stronger client-side and production-oriented privacy architectures.

## References

1. J. H. Cheon, A. Kim, M. Kim, and Y. Song. [Homomorphic Encryption for Arithmetic of Approximate Numbers](https://eprint.iacr.org/2016/421.pdf). Cryptology ePrint Archive, 2016/421.
2. A. Al Badawi et al. [OpenFHE: Open-Source Fully Homomorphic Encryption Library](https://eprint.iacr.org/2022/915.pdf). Cryptology ePrint Archive, 2022/915.
3. HomomorphicEncryption.org. [Homomorphic Encryption Security Guidelines](https://homomorphicencryption.org/security-guidelines/).
4. OpenFHE Project. [OpenFHE Development Repository](https://github.com/openfheorg/openfhe-development).
