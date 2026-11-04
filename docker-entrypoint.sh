#!/bin/sh
set -eu

DATA_DIR="${STORYGRAM_DATA_DIR:-/data}"
export STORYGRAM_SCHEMA_DIR="${STORYGRAM_SCHEMA_DIR:-/app/schema}"

if [ "${STORYGRAM_AUTO_INIT:-1}" = "1" ]; then
    if [ ! -d "$DATA_DIR/data" ] || [ ! -f "$DATA_DIR/schema/proposal.schema.json" ]; then
        storygram init "$DATA_DIR"
    fi
    if [ ! -d "$DATA_DIR/.git" ]; then
        git -C "$DATA_DIR" init -q
    fi
    if [ -n "$(git -C "$DATA_DIR" status --porcelain -- schema)" ]; then
        git -C "$DATA_DIR" add -- schema
        git -C "$DATA_DIR" -c "user.name=${GIT_AUTHOR_NAME:-Storygram}" \
            -c "user.email=${GIT_AUTHOR_EMAIL:-storygram@localhost}" \
            commit -q -m "chore: initialize Storygram schema"
    fi
fi

git config --global --add safe.directory "$DATA_DIR" 2>/dev/null || true

exec "$@"
