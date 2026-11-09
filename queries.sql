-- Stage 4: SQL queries run by hand against tasks.db
-- (in DB Browser for SQLite: Execute SQL tab). Changes show up in the API right away.

-- List every task
SELECT * FROM tasks;

-- Show only completed tasks
SELECT * FROM tasks WHERE done = 1;

-- Count all tasks
SELECT COUNT(*) FROM tasks;

-- Mark every task as completed
UPDATE tasks SET done = 1;

-- Delete all completed tasks
DELETE FROM tasks WHERE done = 1;
