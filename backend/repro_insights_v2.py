import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func, case
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

# Use in-memory SQLite
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_phone = Column(String(32))
    amount = Column(Float)
    ts = Column(DateTime, default=datetime.utcnow)
    txn_type = Column(String(16))

Base.metadata.create_all(bind=engine)

def get_month_column(column, db_session):
    """Returns a SQL expression for 'YYYY-MM' formatting based on the database dialect."""
    dialect_name = db_session.bind.dialect.name
    if dialect_name == "sqlite":
        return func.strftime("%Y-%m", column)
    # Default to MySQL/compatible
    return func.date_format(column, "%Y-%m")

def test_fix():
    session = SessionLocal()
    # Add dummy data
    session.add(Transaction(user_phone="123", amount=100.0, txn_type="debit"))
    session.commit()

    try:
        # Use the logic from the fix
        month_fmt = get_month_column(Transaction.ts, session)
        
        q = session.query(month_fmt.label("month")).all()
        print("Query successful with fix!")
        for row in q:
            print(f"Row: {row.month}")
            
    except Exception as e:
        print(f"FAILED with error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    test_fix()
