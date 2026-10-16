# Institutional model validation gate

The application system and the lending model have separate acceptance gates. The current logistic-regression model uses a public research dataset and is **not validated for Ethiopian lending or any institution's production decisions**.

An institution must provide legally obtained, quality-controlled historical applications with the seven model inputs, the decision date, product/branch context, outcomes observed over the agreed performance window, and an unambiguous default definition. Data must support development, validation, independent test, and later out-of-time cohorts without customer overlap. The institution must document missingness, rejects and selection bias, policy changes, fraud handling, recoveries, and label maturity.

`ml.institutional_validation` measures ROC-AUC, PR-AUC, precision, recall, F1, confusion counts, Brier score, calibration, thresholds, false positives/negatives, and observed/predicted default rates. It must be run on untouched validation/test and out-of-time cohorts. Threshold selection belongs to documented credit policy and human governance; a model label does not itself approve or reject an applicant.

`ml.fairness_assessment` evaluates selection rate, error rates, calibration indicators, and predictive performance for legally approved audit groups. Group attributes are validation-only and are not automatically admitted as production features. Small groups are marked insufficient. Results require legal, compliance, domain, and statistical review; the framework is not evidence that the current model is fair.

