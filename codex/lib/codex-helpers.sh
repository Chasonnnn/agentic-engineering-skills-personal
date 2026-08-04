#!/usr/bin/env bash
# codex-helpers.sh: shared helpers for the codex skill. Sourced from bash
# blocks in SKILL.md; never execute directly.
#
# Functions:
#   _codex_auth_probe      — multi-signal auth check (env vars + auth file)
#   _codex_version_check   — warn on known-bad Codex CLI versions
#   _codex_timeout_wrapper — gtimeout -> timeout -> unwrapped fallback
#
# Hygiene: no set -e / set -u / trap / IFS= / PATH= here — this is sourced
# into a caller's shell and must not change its behavior.

# --- Auth probe -------------------------------------------------------------

_codex_auth_probe() {
  # Multi-signal: env vars OR auth file. Avoids false negatives for env-auth
  # users (CI, platform engineers) that a file-only check would reject.
  local _codex_home="${CODEX_HOME:-$HOME/.codex}"
  local _k1 _k2
  _k1=$(printf '%s' "${CODEX_API_KEY:-}" | tr -d '[:space:]')
  _k2=$(printf '%s' "${OPENAI_API_KEY:-}" | tr -d '[:space:]')
  if [ -n "$_k1" ] || [ -n "$_k2" ] || [ -f "$_codex_home/auth.json" ]; then
    echo "AUTH_OK"
    return 0
  fi
  echo "AUTH_FAILED"
  return 1
}

# --- Version check ----------------------------------------------------------

_codex_version_check() {
  # Warn on known-bad Codex CLI versions. Anchored regex prevents false
  # positives like 0.120.10 or 0.120.20 from matching. Update this list when
  # a new Codex CLI version regresses (check github.com/openai/codex issues).
  local _ver
  _ver=$(codex --version 2>/dev/null | head -1)
  [ -z "$_ver" ] && return 0
  if echo "$_ver" | grep -Eq '(^|[^0-9.])0\.120\.(0|1|2)([^0-9.]|$)'; then
    echo "WARN: Codex CLI $_ver has known stdin deadlock bugs. Run: npm install -g @openai/codex@latest"
  fi
}

# --- Timeout wrapper --------------------------------------------------------

_codex_timeout_wrapper() {
  # Resolve wrapper binary: prefer gtimeout (Homebrew coreutils on macOS),
  # fall back to timeout (Linux), else run unwrapped. $1 is the duration in
  # seconds; the rest is the command to run.
  local _duration="$1"
  shift
  local _to
  _to=$(command -v gtimeout 2>/dev/null || command -v timeout 2>/dev/null || echo "")
  if [ -n "$_to" ]; then
    "$_to" "$_duration" "$@"
  else
    "$@"
  fi
}
