#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/.venv"
VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
MODE="${1:-quick}"
TOTAL_STEPS=5
CURRENT_STEP=0

if [[ -t 1 ]]; then
  COLOR_BLUE=$'\033[1;34m'
  COLOR_GREEN=$'\033[1;32m'
  COLOR_YELLOW=$'\033[1;33m'
  COLOR_RED=$'\033[1;31m'
  COLOR_RESET=$'\033[0m'
else
  COLOR_BLUE=""
  COLOR_GREEN=""
  COLOR_YELLOW=""
  COLOR_RED=""
  COLOR_RESET=""
fi

print_usage() {
  cat <<'EOF'
Usage:
  bash cipher/agents/devnex_assistant/run_gui.sh quick
  bash cipher/agents/devnex_assistant/run_gui.sh full

Modes:
  quick  Reuse the existing .venv when present, compile Python files, then run main_gui.py.
  full   Delete the local virtual environment and build artifacts, recreate everything, compile, then run main_gui.py.
EOF
}

print_header() {
  printf '\n%s==================================================%s\n' "$COLOR_BLUE" "$COLOR_RESET"
  printf '%sDevNex Assistant - Local GUI Runner%s\n' "$COLOR_BLUE" "$COLOR_RESET"
  printf '%sMode:%s %s\n' "$COLOR_BLUE" "$COLOR_RESET" "$MODE"
  printf '%sProject:%s %s\n' "$COLOR_BLUE" "$COLOR_RESET" "$PROJECT_ROOT"
  printf '%s==================================================%s\n' "$COLOR_BLUE" "$COLOR_RESET"
}

log_step() {
  CURRENT_STEP=$((CURRENT_STEP + 1))
  printf '\n%s[%d/%d] %s%s\n' "$COLOR_BLUE" "$CURRENT_STEP" "$TOTAL_STEPS" "$1" "$COLOR_RESET"
  printf '    %s\n' "$2"
}

log_done() {
  printf '%s    OK%s\n' "$COLOR_GREEN" "$COLOR_RESET"
}

log_note() {
  printf '%s    NOTE:%s %s\n' "$COLOR_YELLOW" "$COLOR_RESET" "$1"
}

fail() {
  printf '\n%sFAILED:%s %s\n' "$COLOR_RED" "$COLOR_RESET" "$1" >&2
  exit 1
}

on_error() {
  fail "The run stopped while executing step $CURRENT_STEP."
}

require_python() {
  if ! command -v python >/dev/null 2>&1; then
    fail "python was not found in PATH."
  fi
}

clean_workspace() {
  log_step "Clean workspace" "Removing local environments and build artifacts"
  rm -rf \
    "$PROJECT_ROOT/.venv" \
    "$PROJECT_ROOT/venv" \
    "$PROJECT_ROOT/env" \
    "$PROJECT_ROOT/.pytest_cache" \
    "$PROJECT_ROOT/build" \
    "$PROJECT_ROOT/dist" \
    "$PROJECT_ROOT/__pycache__"
  log_done
}

ensure_venv() {
  log_step "Prepare virtual environment" "Checking for a local .venv"
  if [[ ! -x "$VENV_PYTHON" ]]; then
    log_note "No reusable .venv found. Creating a fresh one."
    python -m venv "$VENV_DIR"
  else
    log_note "Reusing existing .venv."
  fi
  log_done
}

install_dependencies() {
  log_step "Install dependencies" "Upgrading packaging tools and syncing project dependencies"
  "$VENV_PYTHON" -m pip install --upgrade pip setuptools wheel
  "$VENV_PYTHON" -m pip install -r "$PROJECT_ROOT/requirements.txt" -e "$PROJECT_ROOT"
  log_done
}

seed_runtime_config() {
  log_step "Prepare runtime config" "Creating generated_artifacts/config.json if needed"
  mkdir -p "$PROJECT_ROOT/generated_artifacts"
  "$VENV_PYTHON" -c "from persistence.config_store import ConfigStore, DEFAULT_CONFIG; ConfigStore().save(DEFAULT_CONFIG)"
  log_done
}

compile_project() {
  log_step "Compile project" "Byte-compiling Python sources for a fast sanity check"
  "$VENV_PYTHON" -m compileall -q "$PROJECT_ROOT"
  log_done
}

run_gui() {
  log_step "Launch GUI" "Starting main_gui.py"
  cd "$PROJECT_ROOT"
  "$VENV_PYTHON" "$PROJECT_ROOT/main_gui.py"
}

main() {
  trap on_error ERR
  print_header
  require_python

  case "$MODE" in
    quick)
      ensure_venv
      install_dependencies
      seed_runtime_config
      compile_project
      run_gui
      ;;
    full)
      clean_workspace
      ensure_venv
      install_dependencies
      seed_runtime_config
      compile_project
      run_gui
      ;;
    -h|--help|help)
      print_usage
      ;;
    *)
      printf '%sERROR:%s unknown mode %q\n' "$COLOR_RED" "$COLOR_RESET" "$MODE" >&2
      print_usage
      exit 1
      ;;
  esac
}

main "$@"
