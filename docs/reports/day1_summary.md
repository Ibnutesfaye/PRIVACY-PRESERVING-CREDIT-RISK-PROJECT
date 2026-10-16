# Day 1 Data and Normal-ML Report

## Dataset

- Rows: 32,581 raw; 32,416 after removing 165 exact full-row duplicates.
- Columns: 12.
- Missing values: `person_emp_length` 895; `loan_int_rate` 3,116; all other columns 0.
- Target: 25,473 class 0 (78.18%) and 7,108 class 1 (21.82%).
- Invalid/suspicious values: five ages outside 18–100; maximum age 144 and maximum employment length 123 require domain review.
- Categorical cardinalities: home ownership 4, loan intent 6, loan grade 7, prior default flag 2.
- Leakage concern: `loan_grade` may represent an underwriting decision closely tied to the outcome, so it is excluded from the first numerical/FHE model.

The complete ranges, IQR outlier counts, dtypes, and category values are in `dataset_analysis.json`.

## Preprocessing

Seven numerical features are used: age, income, employment length, loan amount, interest rate, loan-to-income ratio, and credit-history length. The split is stratified 80/20 with random seed 42. Median imputation and `StandardScaler` are fitted only on the 25,932 training records, then applied unchanged to 6,484 test records.

## Baseline result

| Metric | Measured value |
| --- | ---: |
| Accuracy | 0.83205 |
| Precision | 0.70692 |
| Recall | 0.39633 |
| F1 | 0.50791 |
| ROC-AUC | 0.83142 |
| Confusion matrix | [[4833, 233], [856, 562]] |

The relatively low class-1 recall is an honest limitation of this unweighted seven-feature baseline and should be evaluated before changing thresholds or class weights.

## Extracted mathematical model

For scaled input `x`, the logit is `z = dot(weights, x) + bias`.

Weights in feature order:

```text
[0.04532915891805543,
 -0.004971391043297565,
 -0.10685566608167416,
 -0.5493410143686471,
  0.9448311085798077,
  1.2425285058756619,
 -0.030814638728595172]
```

Bias: `-1.7227605924793603`.

Manual logits and sigmoid probabilities match scikit-learn with maximum absolute error `0.0` on the test set.

## OpenFHE acceptance test

OpenFHE v1.5.1 compiled using MSYS2 MinGW64 GCC 16.1.0. The official CKKS `simple-real-numbers` example ran with ring dimension 16,384 and correctly decrypted addition, subtraction, plaintext multiplication, ciphertext multiplication, and rotations.

