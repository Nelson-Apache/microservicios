import models
import schemas
from fastapi import FastAPI, Depends
from database import engine, SessionLocal, Base
from sqlalchemy.orm import Session

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Empleados Service")

def get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

@app.post("/empleados", response_model=schemas.EmpleadoResponse)
def crear_empleado(empleado: schemas.EmpleadoCreate, db: Session = Depends(get_db)):
        db_empleado = models.Empleado(**empleado.model_dump())
        db.add(db_empleado)
        db.commit()
        db.refresh(db_empleado)
        return db_empleado

@app.get("/empleados/{empleado_id}", response_model=schemas.EmpleadoResponse)
def obtener_empleado(empleado_id: int, db: Session = Depends(get_db)):
        return db.query(models.Empleado).filter(models.Empleado.id == empleado_id).first()
