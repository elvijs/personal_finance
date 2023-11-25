-- schema.sql
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    account_type TEXT,
    added_on DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    date DATE,
    description TEXT,
    amount REAL,
    account_id INTEGER,
    added_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT transaction_pk PRIMARY KEY (date, description, amount),
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);
