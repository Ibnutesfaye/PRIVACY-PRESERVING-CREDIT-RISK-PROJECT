from __future__ import annotations


PERMISSIONS = {
    "dashboard.read": "View dashboard summaries",
    "predictions.read": "View privacy-safe prediction metadata",
    "predictions.export": "Export privacy-safe prediction metadata",
    "privacy.read": "View privacy monitoring",
    "fhe.read": "View FHE configuration and metrics",
    "fhe.benchmark": "Run approved FHE benchmarks",
    "model.read": "View model metadata and metrics",
    "model.approve": "Approve validated model versions",
    "model.activate": "Activate, archive, or roll back models",
    "users.read": "View administrator accounts",
    "users.write": "Create and manage administrator accounts",
    "roles.read": "View roles and permissions",
    "roles.write": "Manage roles and permissions",
    "audit.read": "View audit records",
    "security.read": "View and manage security events",
    "reports.export": "Generate and export approved reports",
    "settings.read": "View system settings",
    "settings.write": "Change system settings",
    "organizations.read": "View authorized organizations and branches",
    "organizations.write": "Manage organization and branch configuration",
    "applications.read": "View organization-scoped credit applications",
    "applications.write": "Create and submit credit applications",
    "applications.review": "Review applications and request additional information",
    "applications.approve": "Record authorized human credit decisions",
    "retention.write": "Manage organization retention policies",
}

ROLE_PERMISSIONS = {
    "super_admin": set(PERMISSIONS),
    "ml_fhe_analyst": {
        "dashboard.read", "predictions.read", "privacy.read", "fhe.read",
        "fhe.benchmark", "model.read", "roles.read",
    },
    "auditor": {
        "dashboard.read", "predictions.read", "predictions.export", "privacy.read",
        "fhe.read", "model.read", "roles.read", "audit.read", "security.read",
        "reports.export", "settings.read",
    },
    "support_admin": {
        "dashboard.read", "predictions.read", "privacy.read", "fhe.read",
        "users.read", "security.read",
    },
    "organization_admin": {
        "dashboard.read", "organizations.read", "organizations.write", "applications.read",
        "applications.review", "users.read", "users.write", "reports.export", "settings.read",
        "retention.write",
    },
    "branch_manager": {
        "dashboard.read", "organizations.read", "applications.read", "applications.review",
        "applications.approve", "predictions.read", "reports.export",
    },
    "loan_officer": {
        "dashboard.read", "organizations.read", "applications.read", "applications.write",
        "applications.review", "predictions.read",
    },
    "risk_analyst": {
        "dashboard.read", "organizations.read", "applications.read", "predictions.read",
        "privacy.read", "fhe.read", "model.read", "reports.export",
    },
}

ROLE_DESCRIPTIONS = {
    "super_admin": "Full administrative access",
    "ml_fhe_analyst": "Model, benchmark, and FHE analysis",
    "auditor": "Read-only compliance, audit, and approved export access",
    "support_admin": "Limited operational support visibility",
    "organization_admin": "Organization-scoped user, branch, policy, and reporting administration",
    "branch_manager": "Branch-scoped application review and authorized human decisions",
    "loan_officer": "Branch-scoped application submission and prediction requests",
    "risk_analyst": "Organization portfolio, model, and privacy analysis",
}
