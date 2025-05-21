from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, JSON, DateTime, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from app.config import settings
import re

Base = declarative_base()

class Agency(Base):
    __tablename__ = "agencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    api_key = Column(Text, unique=True, index=True)
    description = Column(Text)
    # Add other fields like: logo_url = Column(Text, name='logoUrl') etc.

    services = relationship("Service", back_populates="agency")
    clients = relationship("Client", back_populates="agency")
    plans = relationship("Plan", back_populates="agency")

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    outcomes = Column(JSON, nullable=False)
    price_lower = Column(Integer)
    price_upper = Column(Integer)
    when_to_recommend = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    # Add other fields like: service_id = Column(String(100), name='serviceId', nullable=False)

    agency = relationship("Agency", back_populates="services")

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(255), nullable=False, index=True)
    website_url = Column(Text)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    # deleted_at = Column(DateTime, nullable=True)

    agency = relationship("Agency", back_populates="clients")
    plans = relationship("Plan", back_populates="client")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    agency_id = Column(Integer, ForeignKey("agencies.id"), nullable=False)
    plan_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="plans")
    agency = relationship("Agency", back_populates="plans")

DATABASE_URL_FROM_SETTINGS = settings.DATABASE_URL

# Re-add sslmode stripping logic for robustness
CLEANED_DATABASE_URL = DATABASE_URL_FROM_SETTINGS
if DATABASE_URL_FROM_SETTINGS and "sslmode=" in DATABASE_URL_FROM_SETTINGS:
    TEMP_URL = re.sub(r"sslmode=[^&]*&?", "", DATABASE_URL_FROM_SETTINGS)
    CLEANED_DATABASE_URL = re.sub(r"\?&", "?", TEMP_URL)
    if CLEANED_DATABASE_URL.endswith("?"):
        CLEANED_DATABASE_URL = CLEANED_DATABASE_URL[:-1]
    if not CLEANED_DATABASE_URL.startswith(DATABASE_URL_FROM_SETTINGS.split("://")[0] + "://"):
        CLEANED_DATABASE_URL = DATABASE_URL_FROM_SETTINGS

# print(f"Using DATABASE_URL for SQLAlchemy: {CLEANED_DATABASE_URL}")

engine = create_async_engine(
    CLEANED_DATABASE_URL, 
    pool_size=5, 
    max_overflow=5,
    pool_recycle=1800,  # Recycle connections every 30 minutes
    pool_pre_ping=True  # Enable pre-ping to check connection liveness
)

AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
