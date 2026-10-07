import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import models
from db.database import get_db
from schemas import ScenarioSessionOut

router = APIRouter(tags=["sessions"])

# Виртуализация и Constructor сознательно отложены (см. CLAUDE.md). Эти эндпоинты
# фиксируют намерение запустить сценарий (Panel п.5) и точку расширения для
# live-наблюдения (Panel п.6, spectator_url), но реальную VM не поднимают.
_NOT_IMPLEMENTED_NOTE = (
    "Constructor и виртуализация ещё не реализованы — сессия создана как заготовка, "
    "реальная машина не поднимается."
)


@router.post(
    "/scenarios/{scenario_id}/sessions",
    response_model=ScenarioSessionOut,
    status_code=202,
)
def launch_scenario(scenario_id: uuid.UUID, db: Session = Depends(get_db)):
    scenario = db.get(models.Scenario, scenario_id)
    if not scenario:
        raise HTTPException(404, "scenario not found")

    session_obj = models.ScenarioSession(
        scenario_id=scenario_id,
        status="awaiting_constructor",
        spectator_url=None,
    )
    db.add(session_obj)
    db.commit()
    db.refresh(session_obj)
    return session_obj


@router.get("/scenarios/{scenario_id}/sessions", response_model=list[ScenarioSessionOut])
def list_scenario_sessions(scenario_id: uuid.UUID, db: Session = Depends(get_db)):
    """Запуск предыдущих сценариев, если ресурсы ещё сохранены (Panel п.5) —
    пока всегда пустой список результатов реального запуска, т.к. ресурсы не создаются."""
    if not db.get(models.Scenario, scenario_id):
        raise HTTPException(404, "scenario not found")
    return (
        db.query(models.ScenarioSession)
        .filter(models.ScenarioSession.scenario_id == scenario_id)
        .order_by(models.ScenarioSession.created_at.desc())
        .all()
    )


@router.get("/sessions/{session_id}", response_model=ScenarioSessionOut)
def get_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.get(models.ScenarioSession, session_id)
    if not obj:
        raise HTTPException(404, "session not found")
    return obj
