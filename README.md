# gaikovert

Площадка для live-debugging собеседований: кандидату выдаётся браузерный доступ к
АРМ (виртуальная машина), на которой заранее воспроизведена рабочая, но неисправная
инфраструктура. Кандидат сам находит и устраняет причину проблемы.

## Компоненты

- **Panel** — backend API: библиотека шаблонов (сервисы, machine-конфигурации),
  сценарии, сессии.
- **PanelUI** — SPA для интервьюера/админа, ходит в Panel API.
- **DB** — Postgres, схему создают init-скрипты в `db/init/`.
- **Front** — удалённый рабочий стол кандидата (Apache Guacamole) — не реализован.
- **Constructor** — создание VM под сценарий (libvirt/KVM) — не реализован.

Подробности и архитектура — в [CLAUDE.md](CLAUDE.md).

## Запуск

```
docker compose up --build db panel panel-ui
docker compose exec panel python seed.py   # демо-сценарий
```

- Panel API: http://localhost:8001/docs
- PanelUI: http://localhost:8002

## Статус

MVP: виртуализация и запуск сценариев — заглушка (ждёт Constructor), оценка —
вживую интервьюером.
