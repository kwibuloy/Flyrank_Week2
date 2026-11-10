# Task API

A small to-do REST API built with [FastAPI](https://fastapi.tiangolo.com/). It supports full CRUD (create, read, update, delete) on tasks, validates input, and returns proper HTTP status codes. Interactive docs come for free via Swagger UI.

Every error response is JSON with an `error` message, e.g. `{"error": "Task 99 not found."}`.

Tasks are stored in **PostgreSQL**, running in Docker with a named volume, so they survive restarts of the app and of the database container. `docker compose up` starts the whole stack. The API (URLs, request bodies and responses) is the same as in Assignments 1 and 2; only the storage changed.

## Quick start

You need [Docker](https://www.docker.com/) with Docker Compose, and `git`.

```bash
git clone https://github.com/kwibuloy/Flyrank_Week2.git
cd Flyrank_Week2
cp .env.example .env
```

Open `.env` and change `change-me` to a password of your own (in both places it appears). Then:

```bash
docker compose up --build
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Postgres: `127.0.0.1:5433` (user, password and database name from `.env`)

The first start creates the database, the `tasks` table and three example tasks. Stop the stack with `Ctrl+C`, or `docker compose down` if you started it with `-d`. Your tasks stay in the volume either way.

## Configuration: `.env`

The connection settings live in `.env`, which is **gitignored**, so the real password is never committed. [`.env.example`](.env.example) is the committed template.

| Variable | Used by | Meaning |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Postgres container, and the app's URL inside compose | Database login and name |
| `POSTGRES_PORT` | docker compose | Host port for Postgres (default `5433`, because `5432` is often taken by another local Postgres) |
| `DATABASE_URL` | The app, when run directly on your machine | Full connection string, e.g. `postgresql://tasks:change-me@127.0.0.1:5433/tasks` |

Inside docker compose the app doesn't use the `DATABASE_URL` from `.env`. Compose builds one that points at the `db` service instead of `127.0.0.1` (see [`docker-compose.yml`](docker-compose.yml)). The app reads `DATABASE_URL` at startup and refuses to start if it's missing.

Use `127.0.0.1`, not `localhost`, in `DATABASE_URL`. On Windows, `localhost` is tried as IPv6 (`::1`) first, and connections stalled there before falling back.

## Architecture: swapping the repository

The code is split into layers. Each layer only talks to the one below it.

| File | Layer | Job |
|---|---|---|
| [`routes.py`](routes.py) | HTTP | Reads the request, calls the service, returns the response |
| [`service.py`](service.py) | Service | Validation rules and error messages |
| [`repositories.py`](repositories.py) | Repository interface | `TaskRepository` (`list`, `get`, `add`, `update`, `delete`) and `InMemoryTaskRepository` |
| [`postgres_repository.py`](postgres_repository.py) | Repository | `PostgresTaskRepository`: the same five methods, using SQL with `%s` parameters |
| [`wiring.py`](wiring.py) | Wiring | The only place that picks which repository the app uses |
| [`main.py`](main.py) | App | Creates the app and maps "not found" to 404 and "invalid" to 400 |

**To be honest about how this happened:** until Assignment 2, everything lived in `main.py`, with the SQL written straight into the route functions, so there was no repository to swap. I did it in two separate commits:

1. **Refactor** (`Refactor into routes, service and repository layers`): split `main.py` into the layers above, with an in-memory repository. This commit did change the routes, by moving them out of `main.py`.
2. **Swap** (`Swap in a Postgres repository`): added `PostgresTaskRepository` and changed `wiring.py` to use it. **`service.py`, `routes.py`, `main.py` and `repositories.py` did not change in this commit.** You can check with:

   ```bash
   git diff ":/Refactor into routes" HEAD -- service.py routes.py main.py repositories.py
   ```

   It prints nothing, because those files are unchanged since the refactor. `git log --stat` shows which files each commit touched.

To check that nothing visible changed, I replayed the same 27 requests three times and diffed the output: against the Week 2 SQLite version, the in-memory refactor, and Postgres. The requests covered every endpoint, every 400 case, and 404s including `/tasks/abc`. All three outputs were identical.

One difference those requests don't hit: Postgres never reuses an id. If you delete the task with the highest id, the next new task still gets a new number. The old SQLite and in-memory versions reused it.

## The database

- **Table:** created by [`db/init.sql`](db/init.sql), which is mounted into the Postgres container's `/docker-entrypoint-initdb.d`. Postgres runs it automatically only when the data volume is empty, so the three example tasks are inserted once. The script is also safe to run again by hand.

  ```sql
  CREATE TABLE IF NOT EXISTS tasks (
      id    INTEGER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
      title TEXT    NOT NULL,
      done  BOOLEAN NOT NULL DEFAULT FALSE
  );
  ```

- **Volume:** the data is in the Docker volume `tasks-pgdata`, mounted at `/var/lib/postgresql/data`. Containers can be stopped, restarted or deleted, and the data stays.
- **Look inside:**

  ```bash
  docker compose exec db psql -U tasks -d tasks -c "SELECT * FROM tasks ORDER BY id;"
  ```

  The practice queries from Assignment 2 are in [`queries.sql`](queries.sql) and work in Postgres too.
- **Reset to the example tasks:** `docker compose down -v` deletes the volume and **all your tasks**. The next `docker compose up` starts fresh.

### Starting Postgres without compose

This is the plain `docker run` equivalent of the `db` service, which I used before writing the compose file. On PowerShell, put the values from your `.env` in place of the `<...>` parts:

```bash
docker run -d --name tasks-db -e POSTGRES_USER=tasks -e POSTGRES_PASSWORD=<your password> -e POSTGRES_DB=tasks -p 127.0.0.1:5433:5432 -v tasks-pgdata:/var/lib/postgresql/data -v "<full path to this folder>/db:/docker-entrypoint-initdb.d:ro" postgres:17
```

### Running the app on your machine instead of in Docker

Start only the database, then run the app with Python 3.10+:

```bash
docker compose up -d db
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

The app reads `DATABASE_URL` from `.env`.

## Proof that data persists

I created rows through the API, restarted **both** the app and the database container, then went further and deleted both containers. The rows were still there each time. Here are the commands and what they returned on 2026-11-10:

**1. Create rows** (the stack is running with `docker compose up -d`):

```bash
curl -X POST localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Persistence check A"}'
curl -X POST localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Persistence check B"}'
curl -X PUT localhost:8000/tasks/7 -H "Content-Type: application/json" -d '{"done":true}'
```

```
{"id":6,"title":"Persistence check A","done":false}
{"id":7,"title":"Persistence check B","done":false}
{"id":7,"title":"Persistence check B","done":true}
```

**2. Restart the app and the database container:**

```bash
docker compose restart
curl localhost:8000/tasks
```

Both rows were still returned, including task 7's `"done": true`.

**3. Delete both containers, then start new ones:**

```bash
docker compose down      # removes the app and db containers (not the volume)
docker compose ps -a     # nothing left
docker compose up -d     # new containers, same volume
curl localhost:8000/tasks
```

The container IDs changed (`34f81a882b9f`, `45e66dfd3769` before; `7e7b80f5e178`, `ac5c17405153` after), and `GET /tasks` still returned the same six tasks. Checking Postgres directly showed the same:

```
 id |        title        | done
----+---------------------+------
  1 | Workout             | f
  2 | Eat                 | t
  3 | Shower              | t
  5 | Padded title        | f
  6 | Persistence check A | f
  7 | Persistence check B | t
(6 rows)
```

Task 5 came from the 27-request check, run earlier against the same database, which created and deleted task 4.

## Endpoints

| Method | Path          | Description                          | Success | Errors |
|--------|---------------|--------------------------------------|---------|--------|
| GET    | `/`           | API name, version and endpoints      | `200`   |        |
| GET    | `/health`     | Health check                         | `200`   |        |
| GET    | `/tasks`      | List all tasks                       | `200`   |        |
| GET    | `/tasks/{id}` | Get one task                         | `200`   | `404` unknown id |
| POST   | `/tasks`      | Create a task from `{"title": "..."}`| `201`   | `400` invalid body or missing/empty title |
| PUT    | `/tasks/{id}` | Replace `title` and/or `done`        | `200`   | `400` empty/invalid body, `404` unknown id |
| DELETE | `/tasks/{id}` | Delete a task (empty body)           | `204`   | `404` unknown id |

A task looks like this:

```json
{ "id": 1, "title": "Workout", "done": false }
```

## Example

```bash
curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Buy milk"}'
```

```
HTTP/1.1 201 Created
server: uvicorn
content-length: 40
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

More calls to try:

```bash
curl -i -X PUT http://localhost:8000/tasks/4 -H "Content-Type: application/json" -d '{"done":true}'
curl -i -X DELETE http://localhost:8000/tasks/4
curl -i http://localhost:8000/tasks
```

On Windows PowerShell, use `curl.exe` instead of `curl` and escape the inner quotes, e.g. `-d '{\"title\":\"Buy milk\"}'`.

## Swagger UI

Open http://localhost:8000/docs, expand any endpoint, click **Try it out**, then **Execute** to send a real request.

![Swagger UI showing all Task API endpoints](docs/swagger.png)

## History: Assignment 2 used SQLite

Before Postgres, tasks were stored in a SQLite file, `tasks.db`. SQLite was chosen then because it is built into Python, needs no server, and keeps the whole database in one file. That was the right size for learning SQL on a single-user app. Postgres is a step up: a real database server, run the way it would be in production.

The screenshot below is from that version: a read-only view of `tasks.db`, generated with Python's `sqlite3` module and captured with headless Microsoft Edge. Any `tasks.db` left in the folder is no longer used, and it is gitignored.

![SQLite viewer showing the tasks table structure, its rows, and a query result](docs/sqlite-viewer.png)
