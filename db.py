import sqlite3


def get_connection():
    return sqlite3.connect("database.sqlite3")


def migrate():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("PRAGMA user_version")
    version = int(cursor.fetchone()[0])
    print("Current db version is:", version)

    if version < 1:
        cursor.execute(
            """
            CREATE TABLE scrape (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                proxy TEXT NOT NULL,
                url TEXT NOT NULL,
                resp_status INTEGER,
                resp_body TEXT
            )
            """
        )
        cursor.execute("PRAGMA user_version = 1")
    connection.commit()


def run_sql(*args, return_last_insert_rowid=False, **kwargs):
    connection = get_connection()
    cursor = connection.cursor()
    results = list(cursor.execute(*args, **kwargs))
    connection.commit()
    if return_last_insert_rowid:
        return int(list(cursor.execute("select last_insert_rowid();"))[0][0])
    else:
        return results
