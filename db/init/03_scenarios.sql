-- Сценарии: карточки + точечные переопределения шаблонов из библиотеки
-- конкретно под сценарий (arm_override / machine_override / override у сервисов).

CREATE TABLE scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    arm_machine_template_id UUID NOT NULL REFERENCES machine_templates(id),
    arm_override JSONB,
    -- Бриф для интервьюера (CLAUDE.md, Panel п.6) — что должно произойти,
    -- чтобы оценивать ход решения вживую.
    briefing_root_cause TEXT,
    briefing_expected_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP DEFAULT now()
);

-- Одна из "сломанных" машин сценария (может быть несколько — микросервисная топология).
CREATE TABLE scenario_target_machines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    machine_template_id UUID NOT NULL REFERENCES machine_templates(id),
    machine_override JSONB,
    fault JSONB,                     -- {"type": "firewalld-block-port", "params": {...}}
    position INT NOT NULL DEFAULT 0
);

-- Сервис из библиотеки, развёрнутый на конкретной target-машине, + override.
CREATE TABLE scenario_target_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_machine_id UUID NOT NULL REFERENCES scenario_target_machines(id) ON DELETE CASCADE,
    service_template_id UUID NOT NULL REFERENCES service_templates(id),
    override JSONB,
    position INT NOT NULL DEFAULT 0
);
