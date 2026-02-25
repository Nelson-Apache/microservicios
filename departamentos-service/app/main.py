from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import engine, SessionLocal, Base
import models, schemas

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Departamentos Service")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/departamentos",
          response_model=schemas.DepartamentoResponse,
          status_code=status.HTTP_201_CREATED)
def crear_departamento(departamento: schemas.DepartamentoCreate, db: Session = Depends(get_db)):
    nuevo_departamento = models.Departamento(**departamento.model_dump())
    db.add(nuevo_departamento)
    db.commit()
    db.refresh(nuevo_departamento)
    return nuevo_departamento

@app.get("/departamentos",
         response_model=list[schemas.DepartamentoResponse])
def listar_departamentos(db: Session = Depends(get_db)):
    return db.query(models.Departamento).all()

@app.get("/departamentos/{id}",
         response_model=schemas.DepartamentoResponse)
def obtener_departamento(id: str, db: Session = Depends(get_db)):
    departamento = db.query(models.Departamento).filter(models.Departamento.id == id).first()
    if not departamento:
        raise HTTPException(status_code=404, detail="Departamento no encontrado")
    return departamento