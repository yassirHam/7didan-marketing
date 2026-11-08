FROM python:3.13-slim AS builder

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv $VIRTUAL_ENV

RUN pip install --no-cache-dir --upgrade pip

# Install CPU-only PyTorch
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch

COPY requirements-docker.txt .

RUN pip install --no-cache-dir -r requirements-docker.txt


FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/model_cache \
    PROMPT_DIR=retrieval_service/src/prompts \
    MODEL_CONFIG=knowledge_base/src/config/model.json \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Runtime system dependency
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python dependencies
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY knowledge_base/__init__.py knowledge_base/__init__.py
COPY knowledge_base/src/embedders/ knowledge_base/src/embedders/
COPY knowledge_base/src/config/model.json knowledge_base/src/config/model.json

COPY retrieval_service/__init__.py retrieval_service/__init__.py
COPY retrieval_service/src/__init__.py retrieval_service/src/__init__.py
COPY retrieval_service/src/api/ retrieval_service/src/api/
COPY retrieval_service/src/chains/ retrieval_service/src/chains/
COPY retrieval_service/src/crm/ retrieval_service/src/crm/
COPY retrieval_service/src/evaluators/ retrieval_service/src/evaluators/
COPY retrieval_service/src/guardrails/ retrieval_service/src/guardrails/
COPY retrieval_service/src/retrieval/ retrieval_service/src/retrieval/
COPY retrieval_service/src/reranking/ retrieval_service/src/reranking/
COPY retrieval_service/src/prompts/ retrieval_service/src/prompts/

EXPOSE 8000

CMD ["uvicorn", "retrieval_service.src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]