from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from commonlib.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

from routers import service_templates, machine_templates, scenarios, sessions

tags_metadata = [
    {
        "name": "service_templates",
        "description": "Библиотека сервисов (nginx, docker, postgres, ...) для сборки сценариев.",
    },
    {
        "name": "machine_templates",
        "description": "Библиотека cloud-init конфигураций машин, роли arm/target.",
    },
    {
        "name": "scenarios",
        "description": "Сценарии дебага: карточки, создание на основе шаблонов с переопределениями.",
    },
    {
        "name": "sessions",
        "description": "Запуск сценария и live-наблюдение — заглушка, ждёт Constructor/виртуализацию.",
    },
]

app = FastAPI(title="gaikovert panel", version="0.1", openapi_tags=tags_metadata)

# MVP: PanelUI обращается к Panel прямо из браузера. allow_origins="*" — временно,
# до того как появится нормальный список доверенных origin'ов.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    # Схему создают init-скрипты в ../db/init/*.sql (применяются postgres-образом
    # при первом старте контейнера) — Panel её не создаёт и не мигрирует.
    logger.info("Panel app ready")


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


app.include_router(service_templates.router)
app.include_router(machine_templates.router)
app.include_router(scenarios.router)
app.include_router(sessions.router)
