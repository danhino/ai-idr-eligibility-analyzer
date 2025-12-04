"""
Database setup and management for ERA IDR Analyzer.
"""
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from datetime import datetime
import pandas as pd

from src.config import DB_PATH, DB_ECHO, SEED_DIR

Base = declarative_base()


class CPTCode(Base):
    """CPT codes table."""
    __tablename__ = "cpt_codes"
    
    code = Column(String(10), primary_key=True)
    description = Column(Text)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CASCode(Base):
    """CAS (Claim Adjustment) codes table."""
    __tablename__ = "cas_codes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    reason_code = Column(String(10), nullable=False)
    group_code = Column(String(2), nullable=False)
    description = Column(Text)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RemarkCode(Base):
    """Remark codes (RARC) table."""
    __tablename__ = "remark_codes"
    
    rarc = Column(String(10), primary_key=True)
    description = Column(Text)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Rule(Base):
    """Eligibility rules table."""
    __tablename__ = "rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_type = Column(String(50), nullable=False)  # e.g., "allowlist", "denylist", "expression"
    expression = Column(Text)  # JSON or Python expression
    notes = Column(Text)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_engine():
    """Create SQLAlchemy engine."""
    return create_engine(f"sqlite:///{DB_PATH}", echo=DB_ECHO)


def init_db():
    """Initialize database and create tables."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session() -> Session:
    """Get database session."""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def load_seed_data(force: bool = False):
    """
    Load seed data from CSV files if they exist.
    Only loads if database is empty (first-time setup) or force=True.
    
    Args:
        force: If True, reload seed data even if database already has records
    """
    session = get_session()
    
    # Check if database already has data (unless forcing)
    if not force:
        has_cpt = session.query(CPTCode).first() is not None
        has_cas = session.query(CASCode).first() is not None
        has_remark = session.query(RemarkCode).first() is not None
        
        # If database already has any data, skip seed loading
        # This prevents re-adding deleted records on app restart
        if has_cpt or has_cas or has_remark:
            session.close()
            return
    
    # Load CPT codes
    cpt_seed_path = SEED_DIR / "cpt_seed.csv"
    if cpt_seed_path.exists():
        try:
            df = pd.read_csv(cpt_seed_path)
            for _, row in df.iterrows():
                existing = session.query(CPTCode).filter_by(code=str(row['code']).strip()).first()
                if not existing:
                    session.add(CPTCode(
                        code=str(row['code']).strip(),
                        description=str(row.get('description', '')).strip(),
                        active=bool(row.get('active', True))
                    ))
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error loading CPT seed data: {e}")
    
    # Load CAS codes
    cas_seed_path = SEED_DIR / "cas_seed.csv"
    if cas_seed_path.exists():
        try:
            df = pd.read_csv(cas_seed_path)
            for _, row in df.iterrows():
                existing = session.query(CASCode).filter_by(
                    reason_code=str(row['reason_code']).strip(),
                    group_code=str(row['group_code']).strip()
                ).first()
                if not existing:
                    session.add(CASCode(
                        reason_code=str(row['reason_code']).strip(),
                        group_code=str(row['group_code']).strip(),
                        description=str(row.get('description', '')).strip(),
                        active=bool(row.get('active', True))
                    ))
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error loading CAS seed data: {e}")
    
    # Load Remark codes
    remark_seed_path = SEED_DIR / "remark_seed.csv"
    if remark_seed_path.exists():
        try:
            df = pd.read_csv(remark_seed_path)
            for _, row in df.iterrows():
                existing = session.query(RemarkCode).filter_by(rarc=str(row['rarc']).strip()).first()
                if not existing:
                    session.add(RemarkCode(
                        rarc=str(row['rarc']).strip(),
                        description=str(row.get('description', '')).strip(),
                        active=bool(row.get('active', True))
                    ))
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error loading Remark seed data: {e}")
    
    session.close()

