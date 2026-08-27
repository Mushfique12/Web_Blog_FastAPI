from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Setting up the Path for the Database
SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"

# Connection to the Database
# SQLite only allows single thread (hence False)
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Factory that creates Database Sessions (Session - transaction with the DB, each Request gets its own Session)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Dependency Fn that provides sessions to routes
def get_db():
    with SessionLocal() as db:
        yield db