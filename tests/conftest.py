"""Keep pytest temp dirs inside the project (owner rule: nothing outside this folder)."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if not config.option.basetemp:
        config.option.basetemp = str(ROOT / ".tools" / "pytest-tmp")
