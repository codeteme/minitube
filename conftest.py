import os

# Set a dummy DATABASE_URL so service modules can be imported without a real
# database. SQLAlchemy's create_engine is lazy and won't connect until a query
# is actually executed.
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost:5432/testdb")
