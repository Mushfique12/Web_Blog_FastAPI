from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Setting up the Path for the Database
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"

# Connection to the Database
# SQLite only allows single thread (hence False)
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Factory that creates Database Sessions (Session - transaction with the DB, each Request gets its own Session)
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# Dependency Fn that provides sessions to routes
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session