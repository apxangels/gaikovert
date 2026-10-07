-- Библиотека шаблонов (CLAUDE.md, "Библиотека шаблонов"): сервисы и
-- machine-конфигурации (cloud-init), отдельно для роли arm и target.

CREATE TABLE service_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,              -- nginx, docker, postgres, prometheus, ...
    base_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE machine_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('arm', 'target')),
    cloud_init TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);
