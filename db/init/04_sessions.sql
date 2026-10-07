-- Заготовка под запуск сценария (Panel п.5) и live-наблюдение (Panel п.6).
-- Виртуализация и Constructor сознательно отложены (см. CLAUDE.md) — status
-- всегда 'awaiting_constructor', пока Constructor не подключён.
CREATE TABLE scenario_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'awaiting_constructor',
    spectator_url TEXT,
    created_at TIMESTAMP DEFAULT now()
);
