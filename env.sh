# Source this before any command: `source env.sh`
# Keeps ALL tooling inside this project folder (owner rule: no global changes).
_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" && pwd)"
export PATH="$_ROOT/.tools/bin:$PATH"
export UV_CACHE_DIR="$_ROOT/.tools/uv-cache"
export UV_PYTHON_INSTALL_DIR="$_ROOT/.tools/python"
export UV_PYTHON_BIN_DIR="$_ROOT/.tools/bin"
export UV_TOOL_DIR="$_ROOT/.tools/uv-tools"
export UV_TOOL_BIN_DIR="$_ROOT/.tools/bin"
export UV_NO_CONFIG=1
export UV_PYTHON_PREFERENCE=only-managed
export OLLAMA_MODELS="$_ROOT/.tools/ollama-models"
export WB_PROJECT_ROOT="$_ROOT"
