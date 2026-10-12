import os
import uuid
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from commonlib.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

from drivers.vm import get_driver, MachineHandle
from drivers.guacamole import GuacamoleClient

app = FastAPI(title="gaikovert constructor", version="0.1")

_vm_driver = get_driver()
_guac = GuacamoleClient(
    base_url=os.environ.get("GUACAMOLE_BASE_URL", "http://guacamole:8080/guacamole"),
    public_base_url=os.environ.get("GUACAMOLE_PUBLIC_URL"),
    admin_user=os.environ.get("GUACAMOLE_ADMIN_USER", "guacadmin"),
    admin_password=os.environ.get("GUACAMOLE_ADMIN_PASSWORD", "guacadmin"),
    data_source=os.environ.get("GUACAMOLE_DATA_SOURCE", "postgresql"),
)

# session_id -> ресурсы для teardown. In-memory, не переживает перезапуск
# Constructor — осознанное ограничение MVP (см. CLAUDE.md, "Вне рамок MVP").
_sessions: dict[str, dict] = {}


class ServiceSpec(BaseModel):
    type: str
    base_config: dict = {}
    override: Optional[dict] = None


class MachineSpec(BaseModel):
    """
    cloud_init здесь — уже полностью готовый cloud-init (Panel собрал его из
    machine-шаблона + override, и "влил" туда provision/fault/services как
    package/write_files/runcmd). Constructor не ходит отдельно разворачивать
    сервисы или применять fault — это часть cloud-init, которую он просто
    передаёт VMDriver-у при создании машины.
    """

    role: Literal["arm", "target"]
    name: str
    cloud_init: str
    override: Optional[dict] = None
    fault: Optional[dict] = None
    services: list[ServiceSpec] = []


class SessionCreateRequest(BaseModel):
    session_id: uuid.UUID
    arm_machine: MachineSpec
    target_machines: list[MachineSpec] = []


class GuacCredentials(BaseModel):
    username: str
    password: str
    connection_identifier: str


class MachineInfo(BaseModel):
    role: str
    name: str
    ip: str


class SessionCreateResponse(BaseModel):
    status: Literal["ready"]
    guacamole_base_url: str
    candidate: GuacCredentials
    interviewer: GuacCredentials
    machines: list[MachineInfo]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/sessions", response_model=SessionCreateResponse, status_code=201)
def create_session(payload: SessionCreateRequest):
    session_id = str(payload.session_id)
    if session_id in _sessions:
        raise HTTPException(409, "session already provisioned")

    logger.info("provisioning session %s", session_id)

    created_machines: list[MachineHandle] = []
    machine_infos: list[MachineInfo] = []
    try:
        arm_handle = _vm_driver.create_machine(
            role="arm",
            name=payload.arm_machine.name,
            cloud_init=payload.arm_machine.cloud_init,
            override=payload.arm_machine.override,
        )
        created_machines.append(arm_handle)
        machine_infos.append(MachineInfo(role="arm", name=payload.arm_machine.name, ip=arm_handle.ip))

        for tm in payload.target_machines:
            handle = _vm_driver.create_machine(
                role="target", name=tm.name, cloud_init=tm.cloud_init, override=tm.override
            )
            created_machines.append(handle)
            machine_infos.append(MachineInfo(role="target", name=tm.name, ip=handle.ip))

        # Front подключается к машине-АРМ (см. CLAUDE.md, "Целевая платформа") —
        # поэтому Guacamole-connection'ы смотрят именно на неё, не на target.
        candidate_conn_id = _guac.create_connection(
            name=f"{session_id}-candidate", hostname=arm_handle.ip, port=5900, read_only=False
        )
        interviewer_conn_id = _guac.create_connection(
            name=f"{session_id}-interviewer", hostname=arm_handle.ip, port=5900, read_only=True
        )

        candidate_user = f"{session_id}-candidate"
        interviewer_user = f"{session_id}-interviewer"
        candidate_password = _guac.create_scoped_user(candidate_user, candidate_conn_id)
        interviewer_password = _guac.create_scoped_user(interviewer_user, interviewer_conn_id)
    except Exception:
        logger.exception("provisioning session %s failed, rolling back", session_id)
        for handle in created_machines:
            _vm_driver.destroy_machine(handle)
        raise HTTPException(502, "provisioning failed")

    _sessions[session_id] = {
        "machines": created_machines,
        "connections": [candidate_conn_id, interviewer_conn_id],
        "users": [candidate_user, interviewer_user],
    }

    return SessionCreateResponse(
        status="ready",
        guacamole_base_url=_guac.public_base_url,
        candidate=GuacCredentials(
            username=candidate_user, password=candidate_password, connection_identifier=candidate_conn_id
        ),
        interviewer=GuacCredentials(
            username=interviewer_user, password=interviewer_password, connection_identifier=interviewer_conn_id
        ),
        machines=machine_infos,
    )


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    resources = _sessions.get(session_id)
    if not resources:
        raise HTTPException(404, "session not found")
    return {
        "machines": [h.model_dump() for h in resources["machines"]],
        "connections": resources["connections"],
    }


@app.delete("/sessions/{session_id}", status_code=204)
def destroy_session(session_id: str):
    resources = _sessions.pop(session_id, None)
    if not resources:
        raise HTTPException(404, "session not found")

    for conn_id in resources["connections"]:
        _guac.delete_connection(conn_id)
    for username in resources["users"]:
        _guac.delete_user(username)
    for handle in resources["machines"]:
        _vm_driver.destroy_machine(handle)
