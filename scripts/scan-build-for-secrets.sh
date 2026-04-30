#!/usr/bin/env bash
# Scan the production build for accidentally-bundled secrets.
# Run AFTER `npm run build` in web/.
# Exit 1 on any hit. Run from repo root.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${REPO_ROOT}/web/dist"

if [[ ! -d "${BUILD_DIR}" ]]; then
  echo "ERROR: ${BUILD_DIR} does not exist. Run 'npm run build' in web/ first." >&2
  exit 2
fi

# Word-boundaried patterns to avoid false matches on similar-looking strings.
PATTERNS=(
  '\bsk_live_[A-Za-z0-9]{20,}\b'
  '\bsk_test_[A-Za-z0-9]{20,}\b'
  '\brk_live_[A-Za-z0-9]{20,}\b'
  '\brk_test_[A-Za-z0-9]{20,}\b'
  '\bre_[A-Za-z0-9_-]{20,}\b'
  '\bAKIA[0-9A-Z]{16}\b'
  '\bSG\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b'
  '\bxox[abprs]-[A-Za-z0-9-]{10,}\b'
  '\bgithub_pat_[A-Za-z0-9_]{20,}\b'
  '\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b'
  'postgres://[^@[:space:]]+:[^@[:space:]]+@[^/[:space:]]+'
  'mysql://[^@[:space:]]+:[^@[:space:]]+@[^/[:space:]]+'
)

EXIT=0
for PAT in "${PATTERNS[@]}"; do
  if hits="$(grep -REn --include='*.js' --include='*.css' --include='*.html' --include='*.map' --binary-files=without-match "${PAT}" "${BUILD_DIR}" 2>/dev/null || true)"; then
    if [[ -n "${hits}" ]]; then
      echo "=== Pattern: ${PAT} ==="
      echo "${hits}"
      echo
      EXIT=1
    fi
  fi
done

if [[ "${EXIT}" -eq 0 ]]; then
  echo "OK: no secret patterns matched in ${BUILD_DIR}"
fi
exit "${EXIT}"
