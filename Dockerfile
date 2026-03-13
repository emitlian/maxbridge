FROM python:3.11-slim

WORKDIR /workspace

COPY pyproject.toml README.md ./
COPY maxbridge ./maxbridge

RUN pip install --no-cache-dir -e .

CMD ["maxbridge", "--help"]
