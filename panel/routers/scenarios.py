import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from db import models
from db.database import get_db
from schemas import ScenarioDetailOut, ScenarioIn, ScenarioCardOut

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


def _get_scenario_or_404(scenario_id: uuid.UUID, db: Session) -> models.Scenario:
    obj = (
        db.query(models.Scenario)
        .options(
            joinedload(models.Scenario.arm_machine_template),
            joinedload(models.Scenario.target_machines)
            .joinedload(models.ScenarioTargetMachine.machine_template),
            joinedload(models.Scenario.target_machines)
            .joinedload(models.ScenarioTargetMachine.services)
            .joinedload(models.ScenarioTargetService.service_template),
        )
        .filter(models.Scenario.id == scenario_id)
        .first()
    )
    if not obj:
        raise HTTPException(404, "scenario not found")
    return obj


def _to_detail(scenario: models.Scenario) -> ScenarioDetailOut:
    """Собирает ответ вручную: нужны производные поля (имена шаблонов), которых
    нет напрямую в колонках ORM-модели."""
    return ScenarioDetailOut(
        id=scenario.id,
        slug=scenario.slug,
        title=scenario.title,
        arm_machine_template_id=scenario.arm_machine_template_id,
        arm_machine_template_name=scenario.arm_machine_template.name,
        arm_override=scenario.arm_override,
        briefing_root_cause=scenario.briefing_root_cause,
        briefing_expected_steps=scenario.briefing_expected_steps or [],
        created_at=scenario.created_at,
        target_machines=[
            {
                "id": tm.id,
                "name": tm.name,
                "machine_template_id": tm.machine_template_id,
                "machine_template_name": tm.machine_template.name,
                "machine_override": tm.machine_override,
                "fault": tm.fault,
                "services": [
                    {
                        "id": svc.id,
                        "service_template_id": svc.service_template_id,
                        "service_template_name": svc.service_template.name,
                        "override": svc.override,
                    }
                    for svc in tm.services
                ],
            }
            for tm in scenario.target_machines
        ],
    )


def _validate_and_build(payload: ScenarioIn, db: Session) -> dict:
    """Проверяет, что все template_id из библиотеки существуют и нужной роли,
    и возвращает данные, готовые для создания/обновления ORM-объектов."""
    arm_template = db.get(models.MachineTemplate, payload.arm_machine_template_id)
    if not arm_template or arm_template.role != "arm":
        raise HTTPException(400, "arm_machine_template_id должен ссылаться на machine_template с role=arm")

    target_machines_data = []
    for position, tm_in in enumerate(payload.target_machines):
        machine_template = db.get(models.MachineTemplate, tm_in.machine_template_id)
        if not machine_template or machine_template.role != "target":
            raise HTTPException(
                400,
                f"target_machines[{position}].machine_template_id должен ссылаться на "
                "machine_template с role=target",
            )

        services_data = []
        for svc_position, svc_in in enumerate(tm_in.services):
            service_template = db.get(models.ServiceTemplate, svc_in.service_template_id)
            if not service_template:
                raise HTTPException(
                    400,
                    f"target_machines[{position}].services[{svc_position}].service_template_id "
                    "не найден в библиотеке сервисов",
                )
            services_data.append(svc_in)

        target_machines_data.append((tm_in, services_data))

    return {"target_machines_data": target_machines_data}


@router.get("", response_model=list[ScenarioCardOut])
def list_scenarios(db: Session = Depends(get_db)):
    """Карточки сценариев для выбора (CLAUDE.md, Panel п.1)."""
    return db.query(models.Scenario).order_by(models.Scenario.created_at.desc()).all()


@router.post("", response_model=ScenarioDetailOut, status_code=201)
def create_scenario(payload: ScenarioIn, db: Session = Depends(get_db)):
    """Создание нового сценария из шаблонов библиотеки с переопределениями
    (CLAUDE.md, Panel п.2 и раздел "Библиотека шаблонов")."""
    if db.query(models.Scenario).filter_by(slug=payload.slug).first():
        raise HTTPException(409, f"scenario '{payload.slug}' already exists")

    validated = _validate_and_build(payload, db)

    scenario = models.Scenario(
        slug=payload.slug,
        title=payload.title,
        arm_machine_template_id=payload.arm_machine_template_id,
        arm_override=payload.arm_override,
        briefing_root_cause=payload.briefing_root_cause,
        briefing_expected_steps=payload.briefing_expected_steps,
    )

    for position, (tm_in, services_data) in enumerate(validated["target_machines_data"]):
        target_machine = models.ScenarioTargetMachine(
            name=tm_in.name,
            machine_template_id=tm_in.machine_template_id,
            machine_override=tm_in.machine_override,
            fault=tm_in.fault,
            position=position,
        )
        for svc_position, svc_in in enumerate(services_data):
            target_machine.services.append(
                models.ScenarioTargetService(
                    service_template_id=svc_in.service_template_id,
                    override=svc_in.override,
                    position=svc_position,
                )
            )
        scenario.target_machines.append(target_machine)

    db.add(scenario)
    db.commit()

    return _to_detail(_get_scenario_or_404(scenario.id, db))


@router.get("/{scenario_id}", response_model=ScenarioDetailOut)
def get_scenario(scenario_id: uuid.UUID, db: Session = Depends(get_db)):
    return _to_detail(_get_scenario_or_404(scenario_id, db))


@router.put("/{scenario_id}", response_model=ScenarioDetailOut)
def update_scenario(scenario_id: uuid.UUID, payload: ScenarioIn, db: Session = Depends(get_db)):
    """MVP: полная замена target_machines/services, а не точечный patch."""
    scenario = _get_scenario_or_404(scenario_id, db)

    existing = db.query(models.Scenario).filter(
        models.Scenario.slug == payload.slug, models.Scenario.id != scenario_id
    ).first()
    if existing:
        raise HTTPException(409, f"scenario '{payload.slug}' already exists")

    validated = _validate_and_build(payload, db)

    scenario.slug = payload.slug
    scenario.title = payload.title
    scenario.arm_machine_template_id = payload.arm_machine_template_id
    scenario.arm_override = payload.arm_override
    scenario.briefing_root_cause = payload.briefing_root_cause
    scenario.briefing_expected_steps = payload.briefing_expected_steps

    scenario.target_machines.clear()
    for position, (tm_in, services_data) in enumerate(validated["target_machines_data"]):
        target_machine = models.ScenarioTargetMachine(
            name=tm_in.name,
            machine_template_id=tm_in.machine_template_id,
            machine_override=tm_in.machine_override,
            fault=tm_in.fault,
            position=position,
        )
        for svc_position, svc_in in enumerate(services_data):
            target_machine.services.append(
                models.ScenarioTargetService(
                    service_template_id=svc_in.service_template_id,
                    override=svc_in.override,
                    position=svc_position,
                )
            )
        scenario.target_machines.append(target_machine)

    db.commit()
    return _to_detail(_get_scenario_or_404(scenario_id, db))


@router.delete("/{scenario_id}", status_code=204)
def delete_scenario(scenario_id: uuid.UUID, db: Session = Depends(get_db)):
    scenario = db.get(models.Scenario, scenario_id)
    if not scenario:
        raise HTTPException(404, "scenario not found")
    db.delete(scenario)
    db.commit()
