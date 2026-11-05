FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    GRADIO_SERVER_NAME=0.0.0.0

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Embeddings locais do Chroma: baixa o modelo ONNX no build para o primeiro start nao depender de rede
RUN python -c "from chromadb.utils.embedding_functions import DefaultEmbeddingFunction; DefaultEmbeddingFunction()(['aquecimento'])"

COPY agent ./agent
COPY app ./app
COPY data/source ./data/source
COPY langgraph.json ./

EXPOSE 7860
CMD ["python", "-m", "app"]
