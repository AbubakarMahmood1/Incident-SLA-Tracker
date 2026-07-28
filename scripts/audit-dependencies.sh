#!/bin/sh
set -eu

command -v uv >/dev/null 2>&1 || {
  echo "uv is required" >&2
  exit 2
}
command -v uvx >/dev/null 2>&1 || {
  echo "uvx is required" >&2
  exit 2
}

requirements_file=$(mktemp)
trap 'rm -f "$requirements_file"' EXIT INT TERM

uv export \
  --locked \
  --all-extras \
  --no-emit-project \
  --format requirements.txt \
  >"$requirements_file"

uvx --from pip-audit==2.10.1 pip-audit \
  --require-hashes \
  --disable-pip \
  --strict \
  --requirement "$requirements_file"
