# Admin Phase 4: Measured Overview

The overview combines two deliberately separate data classes:

- **Measured research data** loaded from the saved 6,484-sample conventional/FHE comparison and baseline metric artifacts.
- **Operational data** loaded from admin audit and security-event tables. Prediction history remains unavailable until the privacy-safe metadata schema is introduced in Phase 5.

Endpoints require `dashboard.read`:

- `GET /api/admin/dashboard/summary`
- `GET /api/admin/dashboard/activity?days=7`
- `GET /api/admin/dashboard/risk-distribution`
- `GET /api/admin/dashboard/fhe-performance`
- `GET /api/admin/dashboard/privacy`

The interface includes measured model cards, an audit-activity chart, test-set risk distribution, OpenFHE stage latency, privacy-control status, provenance labels, loading/error/empty states, and recent safe audit activity. Browser-side encryption and production TLS are labeled planned. Zero incident counts mean no incidents recorded by this prototype, not proof that incidents cannot exist.
