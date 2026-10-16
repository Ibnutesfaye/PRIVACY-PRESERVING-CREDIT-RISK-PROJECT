# Detailed threat model

The authoritative control summary is `docs/SECURITY.md`. This document records the data-flow threats for the split protocol.

## Trusted client to API

The client holds plaintext, preprocessing artifacts, and secret key. TLS, authentication, profile integrity, client hardening, and key custody are required. A compromised client can disclose features/results or submit malicious ciphertext. Server schema/bounds limit malformed work but cannot repair a compromised key owner.

## API to evaluator

The evaluator receives the CKKS context, multiplication evaluation keys, exactly seven serialized ciphertexts, and batch count. It does not receive a secret-key path, plaintext/scaled features, or a decrypt command. Threats include context/key mismatch, malformed serialization, depth/resource exhaustion, timing/volume inference, and native vulnerabilities. Controls include profile versioning, allow-listed artifacts, size/batch/time bounds, isolated temporary directories, safe native errors, authentication, and resource-aware deployment.

## API to PostgreSQL

PostgreSQL receives minimized workflow and operational metadata. Threats include scope bypass, SQL/application flaws, privileged operator abuse, backup disclosure, and retention failures. Controls include SQLAlchemy parameterization, permission and membership checks, foreign keys/indexes, audit hashes, secret files, private networking, and backup checksums. Managed encryption, privileged-access monitoring, PITR, restore testing, and legal policy remain deployment responsibilities.

## Administrator browser

Threats include phishing, token theft, XSS, CSRF-like cross-origin abuse, privilege escalation, and unrestricted export. Controls include short access tokens, rotating session-stored refresh secrets, restrictive CORS/CSP/headers, backend authorization, permission-filtered UI, export permissions, and audit events. MFA/SSO, device/session inventory, shared rate limiting, and security analytics remain required.

## Model and decision

Threats include poor recall, bias, drift, inappropriate threshold, approximation misunderstanding, and automation bias. The system separates model recommendation from final human decision, requires override reasons, and states limitations. It does not provide fairness, calibration, causal explanations, or regulatory approval.

## Out of scope / not guaranteed

FHE does not guarantee integrity, availability, anonymity, model secrecy, network security, safe endpoints, or correct human decisions. Host/kernel/hypervisor compromise, client malware, supply-chain compromise, colluding privileged actors, side channels, and disaster recovery require controls beyond this codebase.
