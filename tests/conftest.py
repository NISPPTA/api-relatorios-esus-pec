import importlib
import os
import sys
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_original_cwd = Path.cwd()
with tempfile.TemporaryDirectory() as isolated_cwd:
    os.chdir(isolated_cwd)
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost/test"
    try:
        importlib.import_module("src.db.database")
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        os.chdir(_original_cwd)

from src.db.database import get_db_session
from src.main import create_app


async def no_database_session() -> AsyncGenerator[None]:
    yield None


@pytest.fixture
def app() -> FastAPI:
    application = create_app()
    application.dependency_overrides[get_db_session] = no_database_session
    return application


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
