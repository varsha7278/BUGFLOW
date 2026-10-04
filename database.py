from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# PostgreSQL database connection
DATABASE_URL = "postgresql://postgres:varsha1234@localhost:5432/bugflow_db"

# Database engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    echo=True,

    # Connection Pooling
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

# Database session
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for SQLAlchemy models
Base = declarative_base()