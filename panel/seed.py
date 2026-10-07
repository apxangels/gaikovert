"""
Наполняет библиотеку шаблонов и создаёт демо-сценарий из CLAUDE.md
("на target-машине поднят Docker-контейнер, но firewalld блокирует порт").

Запуск: python seed.py (внутри контейнера panel, после того как БД доступна).
Идемпотентен — повторный запуск не создаёт дублей.
"""

from commonlib.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

from db.database import SessionLocal
from db import models

# Схема уже должна существовать — её создают init-скрипты в ../db/init/*.sql
# при первом старте контейнера postgres.


def get_or_create(db, model, defaults=None, **lookup):
    obj = db.query(model).filter_by(**lookup).first()
    if obj:
        return obj, False
    params = {**lookup, **(defaults or {})}
    obj = model(**params)
    db.add(obj)
    db.flush()
    return obj, True


def main():
    db = SessionLocal()
    try:
        nginx_tpl, created = get_or_create(
            db,
            models.ServiceTemplate,
            name="nginx-basic",
            defaults={"type": "nginx", "base_config": {"listen_port": 80}},
        )
        logger.info("service_template nginx-basic %s", "created" if created else "exists")

        docker_tpl, created = get_or_create(
            db,
            models.ServiceTemplate,
            name="docker-generic",
            defaults={"type": "docker", "base_config": {"image": "nginx:latest", "ports": [8080]}},
        )
        logger.info("service_template docker-generic %s", "created" if created else "exists")

        arm_tpl, created = get_or_create(
            db,
            models.MachineTemplate,
            name="arm-default",
            defaults={
                "role": "arm",
                "cloud_init": "#cloud-config\npackages: [firefox, xterm, git, curl]\n",
            },
        )
        logger.info("machine_template arm-default %s", "created" if created else "exists")

        target_tpl, created = get_or_create(
            db,
            models.MachineTemplate,
            name="oraclelinux9-base",
            defaults={
                "role": "target",
                "cloud_init": "#cloud-config\npackages: [docker, nginx, firewalld]\n",
            },
        )
        logger.info("machine_template oraclelinux9-base %s", "created" if created else "exists")

        db.commit()

        scenario = db.query(models.Scenario).filter_by(slug="docker-firewalld-block").first()
        if scenario:
            logger.info("scenario docker-firewalld-block exists, skip")
            return

        scenario = models.Scenario(
            slug="docker-firewalld-block",
            title="Недоступен сервис в контейнере",
            arm_machine_template_id=arm_tpl.id,
            briefing_root_cause="Порт 8080 закрыт в firewalld на app-server",
            briefing_expected_steps=[
                "проверить доступность порта с АРМ",
                "systemctl status firewalld",
                "firewall-cmd --list-ports",
                "открыть порт и повторно проверить доступность",
            ],
        )
        target_machine = models.ScenarioTargetMachine(
            name="app-server",
            machine_template_id=target_tpl.id,
            fault={"type": "firewalld-block-port", "params": {"port": 8080}},
            position=0,
        )
        target_machine.services.append(
            models.ScenarioTargetService(
                service_template_id=docker_tpl.id,
                override={"image": "myapp:latest", "ports": [8080]},
                position=0,
            )
        )
        scenario.target_machines.append(target_machine)

        db.add(scenario)
        db.commit()
        logger.info("scenario docker-firewalld-block created")
    finally:
        db.close()


if __name__ == "__main__":
    main()
