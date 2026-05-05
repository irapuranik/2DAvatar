"""Database setup with SQLAlchemy — supports PostgreSQL (Supabase) and SQLite fallback."""
import os
from pathlib import Path
from urllib.parse import urlparse, urlunparse, quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase


def _fix_database_url(url: str) -> str:
    """URL-encode the password in a database URI so special chars like @ don't break parsing.

    Supabase passwords often contain @, #, etc. which break standard URI parsing.
    This function safely re-encodes the password component.
    """
    if not url or url.startswith("sqlite"):
        return url

    parsed = urlparse(url)
    if parsed.password:
        # Re-encode the password to handle special characters
        encoded_password = quote_plus(parsed.password)
        # Rebuild the netloc: user:encoded_password@host:port
        if parsed.port:
            netloc = f"{parsed.username}:{encoded_password}@{parsed.hostname}:{parsed.port}"
        else:
            netloc = f"{parsed.username}:{encoded_password}@{parsed.hostname}"
        return urlunparse(parsed._replace(netloc=netloc))

    return url


# Use DATABASE_URL env var if set (PostgreSQL / Supabase), else fall back to SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    # Local dev fallback: SQLite
    _DB_PATH = os.environ.get("SIMLAB_DB_PATH", str(Path(__file__).resolve().parent / "aimii.db"))
    DATABASE_URL = f"sqlite:///{_DB_PATH}"
else:
    DATABASE_URL = _fix_database_url(DATABASE_URL)

# SQLAlchemy engine — configure per dialect
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False  # needed for SQLite + FastAPI

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,  # reconnect stale connections (important for Supabase)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_db_connection() -> None:
    """Execute a trivial query to verify the database is reachable.

    Raises sqlalchemy.exc.OperationalError (or similar) if the connection fails.
    """
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


def init_db():
    """Create all tables if they don't exist, and run lightweight migrations.

    This function intentionally does NOT drop or migrate existing tables.
    Production data must never be auto-dropped — run explicit migrations instead.
    """
    Base.metadata.create_all(bind=engine)
    _run_migrations()


def _run_migrations():
    """Run safe, idempotent ALTER TABLE additions for new columns."""
    import logging
    logger = logging.getLogger(__name__)

    migrations = [
        {
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='practice_sessions' AND column_name='status'",
            "check_sqlite": "PRAGMA table_info(practice_sessions)",
            "alter": "ALTER TABLE practice_sessions ADD COLUMN status VARCHAR(20) DEFAULT 'not_started' NOT NULL",
            "col_name": "status",
        },
        {
            "check": "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='password_hash'",
            "check_sqlite": "PRAGMA table_info(users)",
            "alter": "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)",
            "col_name": "password_hash",
        },
        {
            "check": (
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='cases' AND column_name='viseme_shapes_public_path'"
            ),
            "check_sqlite": "PRAGMA table_info(cases)",
            "alter": "ALTER TABLE cases ADD COLUMN viseme_shapes_public_path VARCHAR(500)",
            "col_name": "viseme_shapes_public_path",
        },
    ]

    is_sqlite = DATABASE_URL.startswith("sqlite")

    with engine.connect() as conn:
        for m in migrations:
            try:
                if is_sqlite:
                    result = conn.execute(text(m["check_sqlite"]))
                    cols = [row[1] for row in result]
                    if m["col_name"] in cols:
                        continue
                else:
                    result = conn.execute(text(m["check"]))
                    if result.fetchone():
                        continue

                conn.execute(text(m["alter"]))
                conn.commit()
                logger.info(f"Migration applied: added '{m['col_name']}' column")
            except Exception as e:
                logger.warning(f"Migration skipped ({m['col_name']}): {e}")
