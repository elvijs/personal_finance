-- schema.sql
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    account_type TEXT,
    added_on DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,
    account_id INTEGER,
    is_shared_expense INTEGER DEFAULT 0, -- 0 for False, 1 for True
    added_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT transaction_pk PRIMARY KEY (date, description, amount),
    FOREIGN KEY (account_id) REFERENCES accounts (id)
);


CREATE TABLE IF NOT EXISTS text_features (
    name TEXT,  -- e.g. "short_description"
    value TEXT,  -- e.g. "Regular grocery shop"
    origin TEXT,  -- e.g. "manual" or "decision_tree_classifier_v1.2"
    added_on DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- the three fields that form a primary key in the transactions table
    t_date DATE NOT NULL,
    t_description TEXT NOT NULL,
    t_amount REAL NOT NULL,
    FOREIGN KEY (t_date, t_description, t_amount) REFERENCES transactions (date, description, amount)
);
