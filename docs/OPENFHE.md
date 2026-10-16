# OpenFHE integration

## Circuit and profile

For standardized `x`, weights `w`, and bias `b`, CKKS computes `z = Σ(wᵢxᵢ)+b`, followed by the selected odd degree-7 sigmoid polynomial. The profile `ckks-balanced-degree7-v1` uses OpenFHE 1.5.1, the default 128-bit classic security setting, depth 6, 50-bit scaling modulus, ring dimension 32,768, and batch capacity 8,192.

## Native commands

`openfhe/src/fhe_protocol.cpp` provides four independent commands:

```text
fhe_protocol setup <public-directory> <private-directory>
fhe_protocol encrypt <context> <public-key> <scaled-csv> <ciphertext-directory>
fhe_protocol evaluate <context> <evaluation-keys> <ciphertext-directory> <result-ciphertext>
fhe_protocol decrypt <context> <secret-key> <result-ciphertext> <count> <scores-csv>
```

Only `evaluate` is used by the server. Its argument list has no secret-key path. The server profile contains context, public key, multiplication evaluation keys, and profile JSON; readiness is false if a secret key is found there. The public API distributes only context and public key—not evaluation or secret keys.

`day2_ckks.cpp` and `day3_fhe_predict.cpp` remain research verification executables. They must not be confused with the production split boundary.

## Build

Windows local builds use MSYS2 MinGW64 and the local `openfhe/install` prefix. `deployment/backend.Dockerfile` builds official OpenFHE v1.5.1 and the protocol natively on Linux. The same Windows executable is never copied into Linux.

```powershell
$env:PATH = "C:\msys64\mingw64\bin;$env:PATH"
& C:\msys64\mingw64\bin\cmake.exe -S openfhe -B openfhe/day2-build-local -DCMAKE_BUILD_TYPE=Release
& C:\msys64\mingw64\bin\cmake.exe --build openfhe/day2-build-local --target fhe_protocol -j 1
```

## Evidence

The 6,484-sample API transport/decryption run returned a 1,050,085-byte ciphertext with no plaintext score. Client decryption differed from prior OpenFHE output by at most `1.481e-11`. Three split-process trials averaged 6,082.27 ms including fresh setup and produced zero classification differences from exact-sigmoid threshold decisions. See `docs/CKKS_PROFILE_VALIDATION.md` and `benchmarks/results/split_protocol.json`.

## Failure handling

Invalid Base64, wrong ciphertext count, excessive size/batch, inactive profile, context/key/serialization failure, timeout, native failure, and missing profile produce bounded safe errors. Native stderr, filesystem paths, context/key material, and request bodies are not returned or logged.
