# Final Test Results

Final command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
..............                                                           [100%]
17 passed
```

Validated behavior includes:

- Required dataset columns and binary target.
- Saved model probability output.
- Python-to-C++ FHE export consistency.
- Day 2 encrypted-logit tolerance.
- Degree-7 polynomial selection criterion and interval coverage.
- Complete 6,484-sample FHE result contract and numerical tolerance.
- FastAPI health and compiled OpenFHE readiness.
- Genuine end-to-end OpenFHE API prediction.
- Training-median preprocessing for nullable employment length and interest rate.
- HTTP 422 rejection of negative income.
- HTTP 422 rejection of negative loan amount.
- HTTP 422 rejection of age zero.
- HTTP 422 rejection of missing required income.
- HTTP 422 rejection of out-of-domain extreme values.

Additional application checks:

- React production build passed.
- React lint passed.
- Live browser submission returned a genuine encrypted prediction.
- Browser console contained no warnings or errors.

Three of the 17 tests verify final README, research-report, threat-model, and demo-document completeness. The remaining 14 exercise data, model, FHE, API, and validation behavior.
