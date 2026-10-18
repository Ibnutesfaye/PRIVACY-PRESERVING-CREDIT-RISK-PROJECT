FROM ubuntu:24.04 AS native-build
ARG DEBIAN_FRONTEND=noninteractive
ARG OPENFHE_VERSION=v1.5.1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential ca-certificates cmake git libomp-dev ninja-build && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 --branch ${OPENFHE_VERSION} https://github.com/openfheorg/openfhe-development.git /src/openfhe
RUN cmake -S /src/openfhe -B /src/openfhe-build -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED=ON -DBUILD_UNITTESTS=OFF -DBUILD_EXAMPLES=OFF -DBUILD_BENCHMARKS=OFF -DCMAKE_INSTALL_PREFIX=/opt/openfhe && cmake --build /src/openfhe-build --parallel 2 && cmake --install /src/openfhe-build
WORKDIR /src/application
COPY openfhe/CMakeLists.txt openfhe/CMakeLists.txt
COPY openfhe/src openfhe/src
COPY openfhe/generated/model_input.h openfhe/generated/model_input.h
COPY openfhe/generated/polynomial_config.h openfhe/generated/polynomial_config.h
RUN cmake -S openfhe -B openfhe/build -G Ninja -DCMAKE_BUILD_TYPE=Release -DOPENFHE_LOCAL_PREFIX=/opt/openfhe && cmake --build openfhe/build --target fhe_protocol day3_fhe_predict --parallel 2

FROM ubuntu:24.04 AS runtime
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libgomp1 libomp5 python3 python3-pip python3-venv && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin cipherscore
WORKDIR /app
COPY requirements.txt .
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir --requirement requirements.txt
COPY backend backend
COPY ml ml
COPY data/raw data/raw
COPY benchmarks/results benchmarks/results
COPY docs/reports docs/reports
COPY data/processed data/processed
COPY alembic.ini .
COPY --from=native-build /opt/openfhe /opt/openfhe
COPY --from=native-build /src/application/openfhe/build/fhe_protocol /app/openfhe/day2-build-local/fhe_protocol.exe
COPY --from=native-build /src/application/openfhe/build/day3_fhe_predict /app/openfhe/day2-build-local/day3_fhe_predict.exe
COPY deployment/backend-entrypoint.sh /usr/local/bin/cipherscore-entrypoint
RUN /opt/venv/bin/python -m ml.preprocess && /opt/venv/bin/python -m ml.train && /opt/venv/bin/python -m ml.extract_model && /opt/venv/bin/python -m ml.polynomial && /opt/venv/bin/python -m ml.validate_artifacts
RUN chmod 0555 /usr/local/bin/cipherscore-entrypoint && chmod +x /app/openfhe/day2-build-local/*.exe && mkdir -p backend/.runtime/fhe-profiles backend/.runtime/encrypted-evaluations && chown -R cipherscore:cipherscore /app/backend/.runtime
ENV PATH="/opt/venv/bin:${PATH}" LD_LIBRARY_PATH="/opt/openfhe/lib:/opt/openfhe/lib64:${LD_LIBRARY_PATH:-}" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER cipherscore
EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/cipherscore-entrypoint"]
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
