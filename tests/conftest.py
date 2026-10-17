import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


import pytest


@pytest.fixture(autouse=True)
def _log_en_tmp(tmp_path, monkeypatch):
    """Ningún test escribe en data/logs real."""
    from core import audit_log

    monkeypatch.setattr(audit_log, "LOG_DIR_DEFAULT", tmp_path / "logs_default")
