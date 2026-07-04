import os
import pytest
from unittest.mock import MagicMock

# 1. Mock load_dotenv so that importing config.py or db.py does not read the developer's local .env
import dotenv
dotenv.load_dotenv = MagicMock(return_value=True)

# 2. Before running any tests, we clean up the PHRONEL_ environment variables at the module level,
# before any other modules are collected/imported by pytest.
for key in list(os.environ.keys()):
    if key.startswith("PHRONEL_"):
        del os.environ[key]

@pytest.fixture(scope="session", autouse=True)
def clean_env():
    # Keep ensuring env is clean during the test session
    for key in list(os.environ.keys()):
        if key.startswith("PHRONEL_"):
            del os.environ[key]
