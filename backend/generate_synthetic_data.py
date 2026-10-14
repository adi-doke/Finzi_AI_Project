# backend/generate_synthetic_data.py
"""
Generate synthetic users, finance summaries and transactions.
Connects to DATABASE_URL (MySQL recommended). If DATABASE_URL is not set,
it will fallback to SQLite at backend/data/dev_transactions.db.
"""

import os
import random
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from faker import Faker
from tqdm import tqdm

from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash

from .database import engine, SessionLocal, Base
from .models import User, FinanceSummary, Transaction

# Config
NUM_USERS = 1000
MONTHS = 6
MIN_PER_MONTH = 20
MAX_PER_MONTH = 30
BATCH_SIZE = 5000  # how many transaction objects to bulk save at once

fake = Faker()
Faker.seed(42)
random.seed(42)


def create_schema():
    print("Creating DB schema (if not exists)...")
    Base.metadata.create_all(bind=engine)


def generate_users(session: Session):
    """
    Generate NUM_USERS users and insert them with hashed passwords.
    Returns list of phone strings inserted.
    """
    users = []
    for i in range(NUM_USERS):
        phone = f"9{random.randint(100000000, 999999999)}"  # random 10-digit-like starting with 9
        users.append({
            "phone": phone,
            "name": fake.name(),
        })

    # deduplicate by phone
    unique = {}
    for u in users:
        unique[u["phone"]] = u
    users = list(unique.values())[:NUM_USERS]

    # Create SQLAlchemy User objects with hashed passwords
    user_objs = []
    for u in users:
        # generate a unique salted hash per user
        password_hash = generate_password_hash("demo123")
        user_objs.append(User(phone=u["phone"], name=u["name"], password=password_hash))

    session.bulk_save_objects(user_objs)
    session.commit()
    print(f"Inserted {len(user_objs)} users.")
    return [u.phone for u in user_objs]


def generate_finance_summaries(session: Session, user_phones):
    fin_objs = []
    for p in user_phones:
        # generate realistic-ish values
        bank = round(random.uniform(500.0, 200000.0), 2)
        mf = round(random.uniform(0.0, 150000.0), 2)
        stocks = round(random.uniform(0.0, 200000.0), 2)
        loan = round(random.uniform(0.0, 150000.0), 2)
        credit_score = random.randint(300, 850)
        fin_objs.append(
            FinanceSummary(
                user_phone=p,
                bank_balance=bank,
                mutual_funds=mf,
                stocks=stocks,
                loan=loan,
                credit_score=credit_score,
            )
        )
    session.bulk_save_objects(fin_objs)
    session.commit()
    print(f"Inserted {len(fin_objs)} finance summaries.")


def random_timestamp_within_month(start_month_dt):
    # start_month_dt is a datetime at the first day of the month
    end_dt = start_month_dt + relativedelta(months=1)
    total_seconds = int((end_dt - start_month_dt).total_seconds())
    offset = random.randint(0, max(0, total_seconds - 1))
    return start_month_dt + timedelta(seconds=offset)


def generate_transactions(session: Session, user_phones):
    txn_categories = [
        "groceries",
        "food",
        "transport",
        "entertainment",
        "utilities",
        "salary",
        "shopping",
        "rent",
        "travel",
        "healthcare",
    ]
    now = datetime.utcnow()
    month_start = (now - relativedelta(months=MONTHS)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    to_insert = []
    total = 0
    print("Generating transactions ...")
    for phone in tqdm(user_phones, desc="users"):
        for m in range(MONTHS):
            m_start = month_start + relativedelta(months=m)
            tx_count = random.randint(MIN_PER_MONTH, MAX_PER_MONTH)
            for _ in range(tx_count):
                amt = round(random.uniform(10.0, 5000.0), 2)
                category = random.choice(txn_categories)
                merchant = fake.company()
                # make salary likely to be credit
                txn_type = (
                    "credit"
                    if category == "salary" and random.random() < 0.95
                    else random.choice(["debit", "credit"])
                )
                desc = fake.sentence(nb_words=6)
                ts = random_timestamp_within_month(m_start)
                to_insert.append(
                    Transaction(
                        user_phone=phone,
                        amount=amt,
                        currency="INR",
                        category=category,
                        merchant=merchant,
                        txn_type=txn_type,
                        description=desc,
                        ts=ts,
                    )
                )
                total += 1

                if len(to_insert) >= BATCH_SIZE:
                    session.bulk_save_objects(to_insert)
                    session.commit()
                    to_insert = []
    if to_insert:
        session.bulk_save_objects(to_insert)
        session.commit()
    print(f"Inserted ~{total} transactions.")


def main():
    create_schema()
    session = SessionLocal()

    # Clear all existing data (clean start)
    print("Dropping existing tables and recreating (clean start).")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    user_phones = generate_users(session)
    generate_finance_summaries(session, user_phones)
    generate_transactions(session, user_phones)
    session.close()
    print("Synthetic data generation complete.")
    if user_phones:
        print("\n" + "="*50)
        print("LOGIN CREDENTIALS For Testing:")
        print(f"Phone:    {user_phones[0]}")
        print(f"Password: demo123")
        print("="*50 + "\n")


if __name__ == "__main__":
    main()
