# Panel

Backend-сервис Panel (см. корневой `CLAUDE.md`). Реализован как FastAPI-приложение
по конвенции `fastapi_template`: `server.py` + `commonlib/` + `*.cfg` + `Dockerfile`.

## Что есть

- Библиотека сервисов (`/service-templates`) и machine-конфигураций
  (`/machine-templates`, роли `arm`/`target`) — CRUD.
- Сценарии (`/scenarios`) — карточки + создание/редактирование сценария на основе
  шаблонов из библиотеки с точечными переопределениями (`override`), как описано
  в CLAUDE.md в разделе "Библиотека шаблонов".
- Заготовка запуска сценария и live-наблюдения (`/scenarios/{id}/sessions`,
  `/sessions/{id}`) — **не поднимает реальную VM**. Виртуализация (libvirt/KVM)
  и Constructor сознательно отложены; статус сессии всегда `awaiting_constructor`.

## Запуск

```
docker compose up --build db panel
```

Затем наполнить библиотеку демо-данными (шаблоны nginx/docker/machine +
сценарий `docker-firewalld-block` из CLAUDE.md):

```
docker compose exec panel python seed.py
```

Swagger UI: http://localhost:8001/docs

## Дальше

- Front и Constructor пока не реализованы.
- Когда будет решено, как поднимать VM — на месте заглушки в `routers/sessions.py`
  появится реальный вызов Constructor API.
