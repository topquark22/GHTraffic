CREATE TABLE IF NOT EXISTS account_credentials (
    token_key         TEXT PRIMARY KEY,
    login             TEXT,
    token_present     INTEGER NOT NULL DEFAULT 1,
    auth_ok           INTEGER NOT NULL DEFAULT 0,
    last_auth_attempt TEXT,
    last_auth_success TEXT,
    last_error        TEXT
);

CREATE INDEX IF NOT EXISTS idx_account_credentials_login
    ON account_credentials(login);
