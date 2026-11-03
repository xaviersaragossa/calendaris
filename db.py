import sqlite3

DB_PATH = "calendaris.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                google_id TEXT PRIMARY KEY,
                email     TEXT NOT NULL,
                name      TEXT,
                token     TEXT NOT NULL   -- JSON de credencials, xifrat
            )"""
        )


def save_user(google_id, email, name, token):
    with _conn() as c:
        c.execute(
            """INSERT INTO users (google_id, email, name, token)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(google_id) DO UPDATE SET
                 email = excluded.email,
                 name  = excluded.name,
                 token = excluded.token""",
            (google_id, email, name, token),
        )


def update_token(google_id, token):
    with _conn() as c:
        c.execute("UPDATE users SET token = ? WHERE google_id = ?", (token, google_id))


def get_user(google_id):
    with _conn() as c:
        return c.execute("SELECT * FROM users WHERE google_id = ?", (google_id,)).fetchone()
