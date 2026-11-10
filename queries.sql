-- Practice queries from Assignment 2. TRUE works in both SQLite and Postgres.
-- Postgres:  docker compose exec db psql -U tasks -d tasks -c "<query>"

-- List every task
SELECT * FROM tasks;

-- Show only completed tasks
SELECT * FROM tasks WHERE done = TRUE;

-- Count all tasks
SELECT COUNT(*) FROM tasks;

-- Mark every task as completed
UPDATE tasks SET done = TRUE;

-- Delete all completed tasks
DELETE FROM tasks WHERE done = TRUE;
