-- schema.sql
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    account_type TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    description TEXT,
    amount REAL,
    account_id INTEGER,
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);
