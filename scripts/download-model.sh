#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
MODEL_NAME="qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/${MODEL_NAME}"
MODEL_SHA256="6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"
MODELS_DIR="${STORYGRAM_MODELS_DIR:-${STORYGRAM_MODEL_DIR:-${ROOT}/models}}"
DESTINATION="${MODELS_DIR}/${MODEL_NAME}"

mkdir -p "${MODELS_DIR}"

if [ -f "${DESTINATION}" ]; then
    if printf '%s  %s\n' "${MODEL_SHA256}" "${DESTINATION}" | sha256sum -c - >/dev/null 2>&1; then
        echo "Model already present and verified: ${DESTINATION}"
        exit 0
    fi
    echo "Existing model failed checksum verification: ${DESTINATION}" >&2
    exit 1
fi

TEMPORARY="${DESTINATION}.part"
rm -f "${TEMPORARY}"
echo "Downloading ${MODEL_URL}"

if command -v wget >/dev/null 2>&1; then
    wget -O "${TEMPORARY}" "${MODEL_URL}"
elif command -v curl >/dev/null 2>&1; then
    curl -fL -o "${TEMPORARY}" "${MODEL_URL}"
else
    echo "Neither wget nor curl is available." >&2
    exit 1
fi

printf '%s  %s\n' "${MODEL_SHA256}" "${TEMPORARY}" | sha256sum -c -
mv "${TEMPORARY}" "${DESTINATION}"
echo "Model ready: ${DESTINATION}"
