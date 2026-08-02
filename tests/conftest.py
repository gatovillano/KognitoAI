import sys
import os
import types
import asyncio
from unittest.mock import MagicMock
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec

os.environ["DATABASE_URL"] = "postgresql+asyncpg://kognito_user:hJxsw8569LJ@localhost:5432/kognito_db"
os.environ.setdefault("DEBUG_MODE", "true")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-1234567890-very-secure")

class DummyLimiter:
    def limit(self, *args, **kwargs):
        return lambda f: f

class DummyMiddleware:
    def __init__(self, app, *args, **kwargs):
        self.app = app
    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)

mock_slowapi = MagicMock()
mock_slowapi.Limiter = lambda *args, **kwargs: DummyLimiter()
mock_slowapi.middleware.SlowAPIMiddleware = DummyMiddleware
mock_slowapi.errors.RateLimitExceeded = Exception
mock_slowapi._rate_limit_exceeded_handler = lambda request, exc: None

sys.modules["slowapi"] = mock_slowapi
sys.modules["slowapi.middleware"] = mock_slowapi.middleware
sys.modules["slowapi.errors"] = mock_slowapi.errors
sys.modules["slowapi.util"] = MagicMock()
sys.modules["limits"] = MagicMock()
sys.modules["limits.errors"] = MagicMock()

class MockModule(types.ModuleType):
    def __getattr__(self, name):
        if name == "__path__":
            return []
        if name == "Tensor":
            class DummyTensor: pass
            return DummyTensor
        val = MagicMock()
        setattr(self, name, val)
        return val

class MockLoader(Loader):
    def create_module(self, spec):
        return MockModule(spec.name)
    def exec_module(self, module):
        pass

class SafeAutoMockFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        allowed_prefixes = (
            "api", "core", "utils", "tests", "extensions", "config",
            "fastapi", "starlette", "pydantic", "pydantic_core",
            "sqlalchemy", "asyncpg", "jwt", "passlib", "slowapi", "limits",
            "pytest", "unittest", "asyncio", "typing", "dataclasses",
            "os", "sys", "uuid", "datetime", "logging", "json", "hashlib",
            "hmac", "re", "math", "time", "contextlib", "inspect", "langchain",
            "openai", "aiofiles", "psycopg", "psycopg_pool", "psycopg_binary",
            "pgvector", "bleach", "xml", "bcrypt", "types", "importlib", "collections",
            "python_multipart", "multipart", "httpx", "greenlet", "_greenlet", "secrets", "test_"
        )
        if any(fullname == p or fullname.startswith(p + ".") or fullname.startswith("test") for p in allowed_prefixes):
            return None
        return ModuleSpec(fullname, MockLoader(), is_package=True)

sys.meta_path.insert(0, SafeAutoMockFinder())

import pytest
from api.main import app

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
