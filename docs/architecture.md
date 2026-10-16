# Architecture

```text
React browser form
  | plaintext over local HTTP (TLS required outside localhost)
  v
Trusted FastAPI client gateway
  | validate -> training-fitted imputer -> training-fitted scaler
  | CKKS encode/encrypt; retains secret key
  v
OpenFHE evaluator boundary
  | receives ciphertext feature columns + plaintext model parameters
  | encrypted weighted sum -> encrypted degree-7 polynomial
  | never receives secret key or plaintext features
  v
Trusted gateway/client decrypts -> clamps display score -> React response
```

The principal demonstrated privacy claim is ciphertext-only evaluation. The browser-to-gateway segment is not end-to-end FHE protected in this prototype and must not be described as such.

