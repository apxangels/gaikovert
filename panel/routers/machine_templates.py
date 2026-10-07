import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db import models
from db.database import get_db
from schemas import MachineTemplateIn, MachineTemplateOut

router = APIRouter(prefix="/machine-templates", tags=["machine_templates"])


@router.get("", response_model=list[MachineTemplateOut])
def list_machine_templates(
    role: Optional[str] = Query(None, pattern="^(arm|target)$"),
    db: Session = Depends(get_db),
):
    query = db.query(models.MachineTemplate)
    if role:
        query = query.filter(models.MachineTemplate.role == role)
    return query.order_by(models.MachineTemplate.name).all()


@router.post("", response_model=MachineTemplateOut, status_code=201)
def create_machine_template(payload: MachineTemplateIn, db: Session = Depends(get_db)):
    if db.query(models.MachineTemplate).filter_by(name=payload.name).first():
        raise HTTPException(409, f"machine template '{payload.name}' already exists")
    obj = models.MachineTemplate(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{template_id}", response_model=MachineTemplateOut)
def get_machine_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.get(models.MachineTemplate, template_id)
    if not obj:
        raise HTTPException(404, "machine template not found")
    return obj


@router.put("/{template_id}", response_model=MachineTemplateOut)
def update_machine_template(template_id: uuid.UUID, payload: MachineTemplateIn, db: Session = Depends(get_db)):
    obj = db.get(models.MachineTemplate, template_id)
    if not obj:
        raise HTTPException(404, "machine template not found")
    for key, value in payload.model_dump().items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{template_id}", status_code=204)
def delete_machine_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.get(models.MachineTemplate, template_id)
    if not obj:
        raise HTTPException(404, "machine template not found")
    db.delete(obj)
    db.commit()
