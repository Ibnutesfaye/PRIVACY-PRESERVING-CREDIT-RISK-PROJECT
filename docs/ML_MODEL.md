# Machine-Learning Model

## Dataset

The source credit-risk dataset contains 32,581 rows and 12 columns. The model uses seven numerical, FHE-friendly features:

1. `person_age`
2. `person_income`
3. `person_emp_length`
4. `loan_amnt`
5. `loan_int_rate`
6. `loan_percent_income`
7. `cb_person_cred_hist_length`

Target: `loan_status`.

## Preprocessing

The pipeline validates/cleans values, selects the seven columns, performs a stratified 80/20 split, fits median imputation and `StandardScaler` on training data only, then transforms training and test partitions with those fitted objects. Saved artifacts are consumed unchanged by the API.

## Why logistic regression

Logistic regression provides a strong, interpretable baseline with an FHE-efficient linear core. `w·x+b` needs additions and ciphertext–plaintext multiplications; only sigmoid requires polynomial approximation. Tree traversal, division, comparison-heavy models, and deep networks would require substantially more complex circuits.

## Measured baseline

| Metric | Value |
|---|---:|
| Training rows | 25,932 |
| Test rows | 6,484 |
| Accuracy | 0.832048 |
| Precision | 0.706918 |
| Recall | 0.396333 |
| F1 | 0.507908 |
| ROC-AUC | 0.831422 |
| Training time | 0.0653 s |

Confusion matrix: `[[4833, 233], [856, 562]]`.

## Reproduction

```powershell
.\.venv\Scripts\python.exe -m ml.inspect_dataset
.\.venv\Scripts\python.exe -m ml.train
.\.venv\Scripts\python.exe -m ml.extract_model
.\.venv\Scripts\python.exe -m ml.export_fhe_inputs
.\.venv\Scripts\python.exe -m ml.export_fhe_batch
```

Reports and plots are written under `docs/reports`; artifacts are generated under ignored `ml/artifacts` and `data/processed` locations.

## Limitations

The model is a research baseline. Recall is materially lower than precision, probability calibration is not established, and no protected-class fairness, subgroup error, temporal drift, external validation, or causal analysis has been performed. It must not be used as the sole basis for lending decisions.
