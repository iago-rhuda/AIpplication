"""Asynchronous SQLAlchemy database session and initialization management."""

from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.config import settings
from src.utils.logger import log_audit_event, logger

Base = declarative_base()

engine = create_async_engine(
    settings.DB_URL,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injector providing an async database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as exc:
            await session.rollback()
            logger.error(f"Database session rolled back due to error: {exc}")
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize SQLite database tables from canonical storage/schema.sql."""
    schema_file = settings.STORAGE_DIR / "schema.sql"
    if not schema_file.exists():
        logger.error(f"Schema file not found at {schema_file}")
        raise FileNotFoundError(f"Schema file not found at {schema_file}")

    schema_sql = schema_file.read_text(encoding="utf-8")
    statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]

    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))

    logger.info(f"Database initialized successfully at {settings.DB_PATH}")
    log_audit_event(
        event_type="DATABASE_INIT",
        entity_type="SYSTEM",
        entity_id="STORAGE",
        action="INITIALIZE_SCHEMA",
        details={"db_path": str(settings.DB_PATH)},
    )
