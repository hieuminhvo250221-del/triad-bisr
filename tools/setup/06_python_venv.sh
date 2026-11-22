#!/usr/bin/env bash
# Python virtual environment with pinned packages (models, verification, plots, slides).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../env.sh"
VENV="$EDA_TOOLS/venv"
[ -x "$VENV/bin/python" ] || /usr/bin/python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --disable-pip-version-check -r "$TRIAD_ROOT/requirements.txt"
mkdir -p "$TRIAD_BUILD/export/env"
"$VENV/bin/python" -m pip freeze --disable-pip-version-check > "$TRIAD_BUILD/export/env/requirements.lock"
"$VENV/bin/python" - <<'PY'
import numpy, scipy, matplotlib, pandas, pytest, cocotb, pptx
print("numpy", numpy.__version__, "| scipy", scipy.__version__, "| matplotlib", matplotlib.__version__,
      "| pandas", pandas.__version__, "| pytest", pytest.__version__, "| cocotb", cocotb.__version__,
      "| python-pptx", pptx.__version__)
PY
