import datetime
import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict


# ---- Библиотека сервисов --------------------------------------------------

class ServiceTemplateIn(BaseModel):
    name: str
    type: str
    base_config: dict[str, Any] = {}


class ServiceTemplateOut(ServiceTemplateIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime.datetime


# ---- Библиотека machine-конфигураций (cloud-init) -------------------------

class MachineTemplateIn(BaseModel):
    name: str
    role: Literal["arm", "target"]
    cloud_init: str


class MachineTemplateOut(MachineTemplateIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime.datetime


# ---- Сценарии ---------------------------------------------------------------

class ScenarioServiceIn(BaseModel):
    service_template_id: uuid.UUID
    override: Optional[dict[str, Any]] = None


class ScenarioServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_template_id: uuid.UUID
    service_template_name: str
    override: Optional[dict[str, Any]] = None


class ScenarioTargetMachineIn(BaseModel):
    name: str
    machine_template_id: uuid.UUID
    machine_override: Optional[dict[str, Any]] = None
    fault: Optional[dict[str, Any]] = None
    services: list[ScenarioServiceIn] = []


class ScenarioTargetMachineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    machine_template_id: uuid.UUID
    machine_template_name: str
    machine_override: Optional[dict[str, Any]] = None
    fault: Optional[dict[str, Any]] = None
    services: list[ScenarioServiceOut] = []


class ScenarioIn(BaseModel):
    slug: str
    title: str
    arm_machine_template_id: uuid.UUID
    arm_override: Optional[dict[str, Any]] = None
    briefing_root_cause: Optional[str] = None
    briefing_expected_steps: list[str] = []
    target_machines: list[ScenarioTargetMachineIn] = []


class ScenarioCardOut(BaseModel):
    """Короткая карточка сценария для списка (CLAUDE.md, Panel п.1)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    created_at: datetime.datetime


class ScenarioDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    arm_machine_template_id: uuid.UUID
    arm_machine_template_name: str
    arm_override: Optional[dict[str, Any]] = None
    briefing_root_cause: Optional[str] = None
    briefing_expected_steps: list[str] = []
    target_machines: list[ScenarioTargetMachineOut] = []
    created_at: datetime.datetime


# ---- Сессии (заглушка, ждёт Constructor) -----------------------------------

class ScenarioSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scenario_id: uuid.UUID
    status: str
    spectator_url: Optional[str] = None
    created_at: datetime.datetime
