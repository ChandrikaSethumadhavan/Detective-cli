FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && git config --system --add safe.directory /repo

WORKDIR /app
COPY pyproject.toml README.md ./
COPY secret_finder ./secret_finder
RUN pip install --no-cache-dir .

WORKDIR /repo
ENTRYPOINT ["secret-finder"]
CMD ["--help"]
