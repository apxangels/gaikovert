import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db import models
from db.database import get_db
from schemas import ServiceTemplateIn, ServiceTemplateOut

router = APIRouter(prefix="/service-templates", tags=["service_templates"])


@router.get("", response_model=list[ServiceTemplateOut])
def list_service_templates(db: Session = Depends(get_db)):
    return db.query(models.ServiceTemplate).order_by(models.ServiceTemplate.name).all()


@router.post("", response_model=ServiceTemplateOut, status_code=201)
def create_service_template(payload: ServiceTemplateIn, db: Session = Depends(get_db)):
    if db.query(models.ServiceTemplate).filter_by(name=payload.name).first():
        raise HTTPException(409, f"service template '{payload.name}' already exists")
    obj = models.ServiceTemplate(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{template_id}", response_model=ServiceTemplateOut)
def get_service_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.get(models.ServiceTemplate, template_id)
    if not obj:
        raise HTTPException(404, "service template not found")
    return obj


@router.put("/{template_id}", response_model=ServiceTemplateOut)
def update_service_template(template_id: uuid.UUID, payload: ServiceTemplateIn, db: Session = Depends(get_db)):
    obj = db.get(models.ServiceTemplate, template_id)
    if not obj:
        raise HTTPException(404, "service template not found")
    for key, value in payload.model_dump().items():
        setattr(obj, key, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{template_id}", status_code=204)
def delete_service_template(template_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.get(models.ServiceTemplate, template_id)
    if not obj:
        raise HTTPException(404, "service template not found")
    db.delete(obj)
    db.commit()
