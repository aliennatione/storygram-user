#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODEL_FILE="qwen2.5-1.5b-instruct-q4_k_m.gguf"
LOCAL_MODELS_DIR="${ROOT}/models"

if [ -z "${STORYGRAM_MODELS_DIR:-}" ]; then
    DATA_SOURCE=$(docker inspect "$(hostname)" \
        --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Source}}{{end}}{{end}}' \
        2>/dev/null || true)
    if [ -n "${DATA_SOURCE}" ]; then
        STORYGRAM_MODELS_DIR="${DATA_SOURCE%/}/models"
    else
        STORYGRAM_MODELS_DIR="${LOCAL_MODELS_DIR}"
    fi
fi

if [ ! -f "${STORYGRAM_MODELS_DIR}/${MODEL_FILE}" ] && [ ! -f "${LOCAL_MODELS_DIR}/${MODEL_FILE}" ]; then
    echo "Model not found: ${STORYGRAM_MODELS_DIR}/${MODEL_FILE}" >&2
    echo "Run ${ROOT}/scripts/download-model.sh first." >&2
    exit 1
fi

export STORYGRAM_MODELS_DIR
export STORYGRAM_LLM_MODEL_FILE="${MODEL_FILE}"
export STORYGRAM_LLM_PROVIDER="openai"
export STORYGRAM_LLM_URL="http://llm:8080"
export STORYGRAM_LLM_MODEL="${MODEL_FILE%.gguf}"
echo "Using host model directory: ${STORYGRAM_MODELS_DIR}"
exec docker compose -f "${ROOT}/compose.yaml" --profile llm "$@" up -d
