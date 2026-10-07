# PanelUI

SPA (React + TypeScript + Vite) для Panel — см. корневой `CLAUDE.md`, раздел "PanelUI".
Ходит в Panel API прямо из браузера.

## Локальная разработка (без Docker)

```
cp .env.example .env     # по умолчанию http://localhost:8001 — подходит, если Panel
                          # поднята через docker compose с её стандартным портом
npm install
npm run dev
```

Откроется на http://localhost:5173.

## Через docker-compose

```
docker compose up --build db panel panel-ui
```

PanelUI соберётся как статика и будет отдаваться nginx на http://localhost:8002.
`VITE_PANEL_API_URL` "запекается" в сборку как build-arg (см. `docker-compose.yml`) —
смена адреса Panel API требует пересборки образа, не просто перезапуска контейнера.

## Экраны

- `/` — карточки сценариев, кнопка создания нового.
- `/scenarios/new` — форма создания сценария: АРМ-шаблон, одна или несколько
  target-машин (machine-шаблон + fault + сервисы с override), бриф для интервьюера.
- `/scenarios/:id` — детали сценария, кнопка "Запустить" и история запусков.
  Пока Constructor не подключён, запуск создаёт заготовку сессии со статусом
  `awaiting_constructor` и без `spectator_url` — UI это явно показывает, а не
  притворяется, что сессия запущена.
- `/library/services`, `/library/machines` — CRUD библиотеки шаблонов.
