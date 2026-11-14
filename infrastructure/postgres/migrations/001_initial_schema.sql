-- Bootstrap a fresh database; preserve existing tables and data.
CREATE TABLE IF NOT EXISTS tasks (
    task_id SERIAL PRIMARY KEY,
    model TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    CONSTRAINT tasks_status_check CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);
