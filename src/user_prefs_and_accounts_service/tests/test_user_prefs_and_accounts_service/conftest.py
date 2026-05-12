import os

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "super-secret-test-key"
os.environ["ALGORITHM"] = "HS256"

# Add these for CI so ConnectionConfig validates during import
os.environ.setdefault("MAIL_USERNAME", "test@example.com")
os.environ.setdefault("MAIL_PASSWORD", "test-password")
os.environ.setdefault("MAIL_FROM", "test@example.com")
os.environ.setdefault("MAIL_PORT", "587")
os.environ.setdefault("MAIL_SERVER", "smtp.example.com")
os.environ.setdefault("MAIL_STARTTLS", "True")
os.environ.setdefault("MAIL_SSL_TLS", "False")

from src.user_prefs_and_accounts_service.main import Base, User, app, get_db