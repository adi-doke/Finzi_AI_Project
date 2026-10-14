import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

# Use in-memory SQLite for reproduction
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

def test_date_format():
    session = SessionLocal()
    # Add dummy data
    session.add(Transaction(user_phone="123", amount=100.0, txn_type="debit"))
    session.commit()

    try:
        # This is the line from insights.py that is expected to fail on SQLite
        month_fmt = func.date_format(Transaction.ts, "%Y-%m")
        q = session.query(month_fmt.label("month")).all()
        print("Query successful (Unexpected for SQLite with date_format)")
    except Exception as e:
        print(f"Caught expected error: {e}")

if __name__ == "__main__":
    test_date_format()
