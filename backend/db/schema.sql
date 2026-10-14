-- backend/db_schema.sql
-- For reference / manual DB creation if needed (Postgres)
CREATE TABLE users (
  phone VARCHAR(32) PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  password VARCHAR(256) NOT NULL,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE finance_summaries (
  id SERIAL PRIMARY KEY,
  user_phone VARCHAR(32) REFERENCES users(phone) ON DELETE CASCADE UNIQUE NOT NULL,
  bank_balance NUMERIC DEFAULT 0,
  mutual_funds NUMERIC DEFAULT 0,
  stocks NUMERIC DEFAULT 0,
  loan NUMERIC DEFAULT 0,
  credit_score INTEGER DEFAULT 0,
  updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE transactions (
  id SERIAL PRIMARY KEY,
  user_phone VARCHAR(32) REFERENCES users(phone) ON DELETE CASCADE NOT NULL,
  amount NUMERIC NOT NULL,
  currency VARCHAR(8) DEFAULT 'INR',
  category VARCHAR(100),
  merchant VARCHAR(200),
  txn_type VARCHAR(16),
  description TEXT,
  ts TIMESTAMP DEFAULT now()
);

CREATE INDEX idx_tx_user_ts ON transactions (user_phone, ts DESC);
