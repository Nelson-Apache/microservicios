from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from . import models, schemas

app = FastAPI(title="Departamentos Service")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/departamentos", response_model=schemas.DepartamentoResponse, status_code=status.HTTP_201_CREATED)
def crear_departamento(departamento: schemas.DepartamentoCreate, db: Session = Depends(get_db)):
    db_departamento = models.Departamento(**departamento.dict())
    db.add(db_departamento)
    db.commit()
    db.refresh(db_departamento)
    return db_departamento

@app.get("/departamentos/{id}", response_model=schemas.DepartamentoResponse)
def obtener_departamento(id: str, db: Session = Depends(get_db)):
    departamento = db.query(models.Departamento).filter(models.Departamento.id == id).first()
    if not departamento:
        raise HTTPException(status_code=404, detail=f"El departamento con id {id} no existe")
    return departamento

@app.get("/departamentos", response_model=list[schemas.DepartamentoResponse])
def listar_departamentos(db: Session = Depends(get_db)):
    return db.query(models.Departamento).all()