# Load-test harness

The k6 smoke profile exercises 1, 10, and 50 concurrent liveness clients. It does not claim encrypted-prediction throughput and does not include credentials or ciphertext fixtures. Run it only against an authorized non-production environment:

```powershell
$env:BASE_URL = "https://pilot-test.example"
k6 run tests/load/k6-smoke.js
```

Add the 100-user scenario only when the host capacity and test authorization permit it. Record actual throughput, latency, errors, queue depth, and memory; never extrapolate or fabricate encrypted inference results from this liveness harness.

`k6-pilot.js` defines sequential 1/10/25/50/100-user stages and mixed liveness, dashboard, and optional encrypted-evaluation traffic. Supply `ACCESS_TOKEN` through the process environment and `ENCRYPTED_FIXTURE` as a pre-generated ciphertext-only JSON string matching the active profile. Never commit either value. Run the 100-user stage only with written authorization and target monitoring for CPU, RAM, PostgreSQL latency, and the application Prometheus metrics. The current synchronous evaluator has no queue, so queue depth is not an available metric; this must not be reported as zero.
