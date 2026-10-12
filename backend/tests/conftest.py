import os

os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")
os.environ.setdefault("COOKIE_SECURE", "false")
os.environ.setdefault("ID_ENCRYPTION_KEYS", "k1:" + "A" * 43 + "=")
os.environ.setdefault("ID_INDEX_KEY", "B" * 43 + "=")
os.environ.setdefault("SCAN_TOKEN_SECRET", "test-secret-not-for-prod")
