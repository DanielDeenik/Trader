# tests/conftest.py
# Shared test fixtures for Social Arb

import os
import shutil
import tempfile

# --- Redirect SQLite to a local (non-FUSE) temp directory BEFORE any social_arb imports ---
_tmp_db_dir = tempfile.mkdtemp(prefix="social_arb_test_")
_tmp_db_path = os.path.join(_tmp_db_dir, "social_arb_test.db")
os.environ["SOCIAL_ARB_DB"] = _tmp_db_path

# Now patch the config singleton and adapter default after import
from social_arb.config import config  # noqa: E402
config.db_path = _tmp_db_path

from social_arb.db import adapter  # noqa: E402
adapter.DEFAULT_DB_PATH = _tmp_db_path

# Initialize the schema so all tables exist
from social_arb.db.schema import init_db  # noqa: E402
init_db(_tmp_db_path)
