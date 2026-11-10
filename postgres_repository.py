"""TaskRepository backed by PostgreSQL.

Implements exactly the same methods as InMemoryTaskRepository, so the service
and routes can't tell which one they are using. Every query uses %s
placeholders, so values are never pasted into SQL text.
"""
from typing import Optional

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from repositories import Task


class PostgresTaskRepository:
    def __init__(self, database_url: str):
        # A small pool of open connections, reused across requests.
        self._pool = ConnectionPool(
            database_url,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
            open=False,
        )
        self._pool.open(wait=True, timeout=30)

    def close(self) -> None:
        self._pool.close()

    def list(self) -> list[Task]:
        with self._pool.connection() as conn:
            return conn.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()

    def get(self, id: int) -> Optional[Task]:
        with self._pool.connection() as conn:
            return conn.execute("SELECT id, title, done FROM tasks WHERE id = %s", (id,)).fetchone()

    def add(self, title: str) -> Task:
        with self._pool.connection() as conn:
            return conn.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, FALSE) RETURNING id, title, done",
                (title,),
            ).fetchone()

    def update(self, id: int, title: Optional[str] = None, done: Optional[bool] = None) -> Optional[Task]:
        # COALESCE keeps the current value for any field that wasn't given.
        with self._pool.connection() as conn:
            return conn.execute(
                """
                UPDATE tasks
                SET title = COALESCE(%s, title),
                    done  = COALESCE(%s, done)
                WHERE id = %s
                RETURNING id, title, done
                """,
                (title, done, id),
            ).fetchone()

    def delete(self, id: int) -> bool:
        with self._pool.connection() as conn:
            return conn.execute("DELETE FROM tasks WHERE id = %s", (id,)).rowcount > 0
