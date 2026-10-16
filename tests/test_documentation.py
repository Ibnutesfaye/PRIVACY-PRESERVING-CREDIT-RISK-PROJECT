from ml.config import PROJECT_ROOT


def test_readme_contains_all_required_sections() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    required = [
        "1. Project overview", "2. Problem statement and motivation", "3. Objectives",
        "4. Dataset", "5. Data preprocessing", "6. Machine learning",
        "7. Homomorphic encryption", "8. Why OpenFHE and CKKS?", "9. System architecture",
        "10. Threat model", "11. FHE inference protocol", "12. Experimental methodology and results",
        "13. Performance analysis", "14. Enterprise workflow", "15. Installation",
        "16. Usage in VS Code", "17. Administrator sign-in", "18. Testing",
        "19. Deployment", "20. Limitations", "21. Future work", "22. Conclusion",
    ]
    for section in required:
        assert f"## {section}" in readme


def test_final_report_contains_twelve_chapters() -> None:
    report = (PROJECT_ROOT / "docs" / "final-research-report.md").read_text(encoding="utf-8")
    for chapter in range(1, 13):
        assert f"## Chapter {chapter} " in report


def test_security_and_demo_documents_exist() -> None:
    assert (PROJECT_ROOT / "docs" / "threat-model.md").is_file()
    assert (PROJECT_ROOT / "docs" / "final-demo-script.md").is_file()


def test_production_documentation_set_exists() -> None:
    required = [
        "PROJECT_ARCHITECTURE.md", "SYSTEM_WORKFLOW.md", "DATABASE.md",
        "API_REFERENCE.md", "OPENFHE.md", "ML_MODEL.md", "SECURITY.md",
        "DEPLOYMENT.md", "BENCHMARKS.md", "CHANGELOG.md",
        "ENCRYPTED_PROTOCOL.md", "CKKS_PROFILE_VALIDATION.md", "DATA_GOVERNANCE.md",
        "LIMITATIONS.md", "BACKUP_AND_RECOVERY.md", "ACCEPTANCE_REPORT.md",
    ]
    for name in required:
        assert (PROJECT_ROOT / "docs" / name).is_file()
