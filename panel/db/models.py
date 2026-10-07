from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Integer, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from db.database import Base

# Схему (таблицы, constraints, extensions) создаёт не SQLAlchemy, а init-скрипты
# в ../db/init/*.sql — они монтируются в /docker-entrypoint-initdb.d контейнера
# postgres и применяются при первом старте БД. Эти ORM-модели только отражают
# ту же схему для чтения/записи из Panel, поэтому id/created_at используют
# server_default, а не python-side default.


class ServiceTemplate(Base):
    """
    Библиотека сервисов (CLAUDE.md, "Библиотека шаблонов"): nginx, docker, postgres,
    prometheus и т.п. У каждого — базовый конфиг, который сценарий переопределяет
    точечно (см. ScenarioTargetService.override) без изменения самого шаблона.
    """

    __tablename__ = "service_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(100), unique=True, nullable=False)
    type = Column(String(50), nullable=False)  # nginx, docker, postgres, prometheus, ...
    base_config = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = Column(DateTime, server_default=text("now()"))


class MachineTemplate(Base):
    """
    Библиотека machine-конфигураций (cloud-init), отдельно для роли "arm"
    (рабочий стол кандидата) и "target" (сломанная машина сценария).
    """

    __tablename__ = "machine_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String(100), unique=True, nullable=False)
    role = Column(String(10), nullable=False)  # "arm" | "target"
    cloud_init = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=text("now()"))


class Scenario(Base):
    """
    Сценарий дебага — карточка, которую выбирают в Panel. Ссылается на шаблоны
    из библиотеки и хранит точечные переопределения конкретно под себя
    (arm_override, machine_override у target-машин, override у сервисов).
    """

    __tablename__ = "scenarios"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    slug = Column(String(100), unique=True, nullable=False)
    title = Column(String(200), nullable=False)

    arm_machine_template_id = Column(UUID(as_uuid=True), ForeignKey("machine_templates.id"), nullable=False)
    arm_override = Column(JSONB, nullable=True)

    # Бриф для интервьюера (CLAUDE.md, Panel п.6) — что должно произойти,
    # чтобы оценивать ход решения вживую.
    briefing_root_cause = Column(Text, nullable=True)
    briefing_expected_steps = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))  # list[str]

    created_at = Column(DateTime, server_default=text("now()"))

    arm_machine_template = relationship("MachineTemplate")
    target_machines = relationship(
        "ScenarioTargetMachine",
        back_populates="scenario",
        cascade="all, delete-orphan",
        order_by="ScenarioTargetMachine.position",
    )


class ScenarioTargetMachine(Base):
    """Одна из "сломанных" машин сценария (может быть несколько — микросервисная топология)."""

    __tablename__ = "scenario_target_machines"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("scenarios.id"), nullable=False)
    name = Column(String(100), nullable=False)
    machine_template_id = Column(UUID(as_uuid=True), ForeignKey("machine_templates.id"), nullable=False)
    machine_override = Column(JSONB, nullable=True)
    fault = Column(JSONB, nullable=True)  # {"type": "firewalld-block-port", "params": {...}}
    position = Column(Integer, nullable=False, default=0)

    scenario = relationship("Scenario", back_populates="target_machines")
    machine_template = relationship("MachineTemplate")
    services = relationship(
        "ScenarioTargetService",
        back_populates="target_machine",
        cascade="all, delete-orphan",
        order_by="ScenarioTargetService.position",
    )


class ScenarioTargetService(Base):
    """Сервис из библиотеки, развёрнутый на конкретной target-машине, + override."""

    __tablename__ = "scenario_target_services"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    target_machine_id = Column(UUID(as_uuid=True), ForeignKey("scenario_target_machines.id"), nullable=False)
    service_template_id = Column(UUID(as_uuid=True), ForeignKey("service_templates.id"), nullable=False)
    override = Column(JSONB, nullable=True)
    position = Column(Integer, nullable=False, default=0)

    target_machine = relationship("ScenarioTargetMachine", back_populates="services")
    service_template = relationship("ServiceTemplate")


class ScenarioSession(Base):
    """
    Заготовка под запуск сценария (Panel п.5) и live-наблюдение (Panel п.6).

    ВАЖНО: реального создания VM здесь нет. Constructor и виртуализация
    (libvirt/KVM) сознательно отложены — см. CLAUDE.md. Статус всегда
    "awaiting_constructor", пока Constructor не будет подключён; поле
    spectator_url всегда пустое.
    """

    __tablename__ = "scenario_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    scenario_id = Column(UUID(as_uuid=True), ForeignKey("scenarios.id"), nullable=False)
    status = Column(String(30), nullable=False, server_default=text("'awaiting_constructor'"))
    spectator_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, server_default=text("now()"))

    scenario = relationship("Scenario")
