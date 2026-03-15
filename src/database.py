"""Database models and session management."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from src.config import settings

Base = declarative_base()


class BuildingOrder(Base):
    """A building work order from the NSW Building Commission register."""

    __tablename__ = "building_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    order_type = Column(String(100), nullable=False)  # e.g. "Stop work order"
    company_name = Column(String(300))
    acn = Column(String(50))
    address = Column(String(500))
    description = Column(Text)
    publication_date = Column(String(50))
    source_url = Column(String(1000), nullable=False)
    pdf_url = Column(String(1000))
    first_seen = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_seen = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (UniqueConstraint("source_url", name="uq_source_url"),)

    def __repr__(self) -> str:
        return f"<BuildingOrder({self.order_type}: {self.company_name})>"


class CrawlLog(Base):
    """Tracks each crawl run."""

    __tablename__ = "crawl_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    finished_at = Column(DateTime)
    orders_found = Column(Integer, default=0)
    new_orders = Column(Integer, default=0)
    status = Column(String(50), default="running")
    error_message = Column(Text)


engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    """Create all database tables."""
    Base.metadata.create_all(engine)


def get_session() -> Session:
    """Get a new database session."""
    return SessionLocal()
