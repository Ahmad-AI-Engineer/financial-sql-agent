"""
seed_data.py  (STEP 2, part 1)
------------------------------
Creates a small but realistic financial database and fills it with random
dummy data. Existing complete demo tables are left unchanged by default:

    python -m src.seed_data

Tables created:
    customers      - people/companies who buy from us
    accounts       - our internal bank/ledger accounts
    invoices       - bills sent to customers
    transactions   - money moving in and out of our accounts
"""

import argparse
import random
from datetime import date, timedelta
from src.db import get_connection

random.seed(42)  # makes the "random" data the same every run (reproducible)

# ---- Reference values used to generate rows ----
COUNTRIES = ["USA", "UK", "Germany", "Pakistan", "India", "Canada", "UAE"]
ACCOUNT_TYPES = ["Checking", "Savings", "Revenue", "Expense"]
CURRENCIES = ["USD", "EUR", "GBP", "PKR"]
INVOICE_STATUS = ["paid", "unpaid", "overdue", "cancelled"]
TXN_TYPES = ["credit", "debit"]
CATEGORIES = ["software", "consulting", "hardware", "salary", "marketing", "travel", "tax"]


# ============================================================
# 1) Create the tables (existing tables are dropped only with --force)
# ============================================================
CREATE_SQL = """
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS invoices CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    customer_id   SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(120) UNIQUE,
    country       VARCHAR(50),
    created_at    DATE NOT NULL
);

CREATE TABLE accounts (
    account_id    SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    type          VARCHAR(20)  NOT NULL,
    currency      VARCHAR(3)   NOT NULL,
    balance       NUMERIC(14,2) NOT NULL DEFAULT 0
);

CREATE TABLE invoices (
    invoice_id    SERIAL PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(customer_id),
    issue_date    DATE NOT NULL,
    due_date      DATE NOT NULL,
    amount        NUMERIC(12,2) NOT NULL,
    status        VARCHAR(20) NOT NULL
);

CREATE TABLE transactions (
    txn_id        SERIAL PRIMARY KEY,
    account_id    INTEGER NOT NULL REFERENCES accounts(account_id),
    customer_id   INTEGER REFERENCES customers(customer_id),
    txn_date      DATE NOT NULL,
    amount        NUMERIC(12,2) NOT NULL,
    type          VARCHAR(10) NOT NULL,
    category      VARCHAR(30),
    description   VARCHAR(200)
);
"""


def random_date(start_days_ago: int, end_days_ago: int) -> date:
    """Return a random date between now-start and now-end (days ago)."""
    today = date.today()
    delta = random.randint(end_days_ago, start_days_ago)
    return today - timedelta(days=delta)


def seed(force: bool = False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name IN ('customers', 'accounts', 'invoices', 'transactions')
                """
            )
            existing_tables = {row["table_name"] for row in cur.fetchall()}
            expected_tables = {"customers", "accounts", "invoices", "transactions"}

            if existing_tables == expected_tables and not force:
                print("Database is already initialized; seed step skipped.")
                return

            if existing_tables and not force:
                raise RuntimeError(
                    "The database has a partial financial schema. "
                    "Run `python -m src.seed_data --force` to rebuild demo data."
                )

            print("Creating tables...")
            cur.execute(CREATE_SQL)

            # ---- customers ----
            print("Inserting customers...")
            customer_ids = []
            for i in range(1, 26):  # 25 customers
                name = f"Customer {i}"
                email = f"customer{i}@example.com"
                country = random.choice(COUNTRIES)
                created = random_date(700, 30)
                cur.execute(
                    "INSERT INTO customers (name, email, country, created_at) "
                    "VALUES (%s, %s, %s, %s) RETURNING customer_id",
                    (name, email, country, created),
                )
                customer_ids.append(cur.fetchone()["customer_id"])

            # ---- accounts ----
            print("Inserting accounts...")
            account_ids = []
            for i in range(1, 7):  # 6 accounts
                name = f"{random.choice(ACCOUNT_TYPES)} Account {i}"
                acc_type = random.choice(ACCOUNT_TYPES)
                currency = random.choice(CURRENCIES)
                balance = round(random.uniform(1000, 500000), 2)
                cur.execute(
                    "INSERT INTO accounts (name, type, currency, balance) "
                    "VALUES (%s, %s, %s, %s) RETURNING account_id",
                    (name, acc_type, currency, balance),
                )
                account_ids.append(cur.fetchone()["account_id"])

            # ---- invoices ----
            print("Inserting invoices...")
            for _ in range(80):  # 80 invoices
                cust = random.choice(customer_ids)
                issue = random_date(365, 5)
                due = issue + timedelta(days=random.choice([15, 30, 45, 60]))
                amount = round(random.uniform(50, 20000), 2)
                status = random.choice(INVOICE_STATUS)
                cur.execute(
                    "INSERT INTO invoices (customer_id, issue_date, due_date, amount, status) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (cust, issue, due, amount, status),
                )

            # ---- transactions ----
            print("Inserting transactions...")
            for _ in range(300):  # 300 transactions
                acc = random.choice(account_ids)
                cust = random.choice(customer_ids + [None])  # some txns have no customer
                txn_date = random_date(365, 0)
                amount = round(random.uniform(10, 15000), 2)
                ttype = random.choice(TXN_TYPES)
                category = random.choice(CATEGORIES)
                desc = f"{category} {ttype} payment"
                cur.execute(
                    "INSERT INTO transactions "
                    "(account_id, customer_id, txn_date, amount, type, category, description) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (acc, cust, txn_date, amount, ttype, category, desc),
                )

        conn.commit()
    print("Done! Dummy financial data is ready.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize the demo financial database.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="drop and rebuild existing demo tables (destructive)",
    )
    seed(force=parser.parse_args().force)
