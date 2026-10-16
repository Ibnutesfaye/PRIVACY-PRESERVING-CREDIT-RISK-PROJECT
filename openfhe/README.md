# OpenFHE Toolchain

OpenFHE v1.5.1 is pinned under the ignored `third_party/openfhe-development`
directory and compiled under `build-final`. Build outputs and dependency source
are not committed.

Windows builds must use MSYS2 MinGW64 because OpenFHE's current Windows guide
states that Visual C++ is no longer supported.

From an MSYS2 MinGW64 shell:

```bash
cd /c/PRIVAC~1
cmake -S openfhe/third_party/openfhe-development -B openfhe/build-final \
  -DBUILD_EXAMPLES=ON \
  -DBUILD_UNITTESTS=OFF \
  -DBUILD_BENCHMARKS=OFF \
  -DBUILD_EXTRAS=OFF \
  -DWITH_OPENMP=OFF \
  -DCMAKE_BUILD_TYPE=Release
cmake --build openfhe/build-final --target simple-real-numbers --parallel 2
export PATH="$PATH:/c/PRIVAC~1/openfhe/build-final/lib"
./openfhe/build-final/bin/examples/pke/simple-real-numbers.exe
```

## Day 2 encrypted weighted sum

Generate the C++ input from the saved Day 1 model in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m ml.export_fhe_inputs
```

Then build and run from MSYS2 MinGW64:

```bash
cd /c/PRIVAC~1
cmake -S openfhe -B openfhe/day2-build-local -DCMAKE_BUILD_TYPE=Release
cmake --build openfhe/day2-build-local --parallel 2
export PATH="$PATH:/c/PRIVAC~1/openfhe/install/lib"
./openfhe/day2-build-local/day2_ckks.exe
```
