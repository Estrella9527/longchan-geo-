"""Root conftest — mock heavy dependencies that aren't available locally."""
import sys
from unittest.mock import MagicMock

# Mock native drivers that may not be installed locally
for mod in ("celery", "celery.result", "asyncpg", "psycopg2", "psycopg2.extensions", "psycopg2.extras"):
    sys.modules.setdefault(mod, MagicMock())

# Mock app.celery_app so execute_task can import it
_mock_celery = MagicMock()
_mock_celery.task = lambda *a, **kw: (lambda f: f)
sys.modules["app.celery_app"] = MagicMock(celery_app=_mock_celery)
