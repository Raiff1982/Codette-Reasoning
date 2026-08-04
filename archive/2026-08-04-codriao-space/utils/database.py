import sqlite3

class Database:
    def __init__(self, db_path=":memory:"):  # Defaults to an in-memory database
        self.connection = sqlite3.connect(db_path)

    def execute(self, sql, params=()):
        cursor = self.connection.cursor()
        cursor.execute(sql, params)
        self.connection.commit()
        return cursor.fetchall()

    def close(self):
        self.connection.close()
