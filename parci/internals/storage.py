"""
Lower level storage implementations.
"""

import json
import sqlite3


class SqliteKV:
    """
    A key-value store that works like a dict and is backed by an SQLite database.
    """

    def __init__(self, db, table="params", serialize_values=True):
        if isinstance(db, sqlite3.Connection):
            self.db = db
        else:
            self.db = sqlite3.connect(db)

        self.table = table
        self.serialize_values = serialize_values
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            """
CREATE TABLE IF NOT EXISTS tkv (
    table_name, key, value,
    UNIQUE (table_name, key) ON CONFLICT REPLACE
)
"""
        )
        self.db.commit()

    def __getitem__(self, item):
        for (v,) in self.db.execute(
            "SELECT value FROM tkv WHERE table_name = ? AND key = ?",
            (
                self.table,
                item,
            ),
        ):
            if self.serialize_values:
                return json.loads(v)
            return v
        raise KeyError("Key does not exist")

    def __setitem__(self, item, value):
        if self.serialize_values:
            value = json.dumps(value)
        self.db.execute(
            "INSERT INTO tkv VALUES (?, ?, ?) ON CONFLICT DO UPDATE SET value = ?",
            (self.table, item, value, value),
        )
        self.db.commit()
        return value

    def __delitem__(self, key):
        self.db.execute(
            "DELETE FROM tkv WHERE table_name = ? AND key = ?",
            (self.table, key),
        )
        self.db.commit()

    def __contains__(self, item):
        for _k in self.db.execute(
            "SELECT key FROM tkv WHERE table_name = ? AND key = ?", (self.table, item)
        ):
            return True
        return False

    def get(self, item, default=None):
        """
        Get a value with a default if the key does not exist.
        """
        try:
            return self[item]
        except KeyError:
            return default

    def keys(self):
        """
        Return a list of all keys.
        """
        return (
            row[0]
            for row in self.db.execute(
                "SELECT key FROM tkv WHERE table_name = ?", (self.table,)
            )
        )

    def values(self):
        """
        Return a list of values.
        """
        for row in self.db.execute(
            "SELECT value FROM tkv WHERE table_name = ?", (self.table,)
        ):
            if self.serialize_values:
                yield json.loads(row[0])
            else:
                yield row[0]

    def items(self):
        """
        Return an iterator over (key, value) pairs.
        """
        for k, v in self.db.execute(
            "SELECT key, value FROM tkv WHERE table_name = ?", (self.table,)
        ):
            if self.serialize_values:
                yield k, json.loads(v)
            else:
                yield k, v

    def __iter__(self):
        return self.keys()
