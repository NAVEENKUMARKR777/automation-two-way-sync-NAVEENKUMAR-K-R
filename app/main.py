import uuid
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas
from .database import Base, engine, get_db


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Work Tracker", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/tasks", response_model=List[schemas.Task])
def list_tasks(db: Session = Depends(get_db)) -> List[models.Task]:
    return db.query(models.Task).all()


@app.post("/tasks", response_model=schemas.Task, status_code=201)
def create_task(task_in: schemas.TaskCreate, db: Session = Depends(get_db)) -> models.Task:
    task = models.Task(
        id=str(uuid.uuid4()),
        title=task_in.title,
        status=task_in.status,
        lead_id=task_in.lead_id,
        notes=task_in.notes,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks/{task_id}", response_model=schemas.Task)
def get_task(task_id: str, db: Session = Depends(get_db)) -> models.Task:
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.put("/tasks/{task_id}", response_model=schemas.Task)
def update_task(task_id: str, task_in: schemas.TaskUpdate, db: Session = Depends(get_db)) -> models.Task:
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_in.title is not None:
        task.title = task_in.title
    if task_in.status is not None:
        task.status = task_in.status
    if task_in.notes is not None:
        task.notes = task_in.notes

    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks/by-lead/{lead_id}", response_model=List[schemas.Task])
def get_tasks_by_lead(lead_id: str, db: Session = Depends(get_db)) -> List[models.Task]:
    return db.query(models.Task).filter(models.Task.lead_id == lead_id).all()


