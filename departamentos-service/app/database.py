from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import time

DATABASE_URL = os.getenv("DATABASE_URL")

# Esperar a que la base de datos esté lista
def wait_for_db():
    retries = 5
    while retries > 0:
        try:
            engine = create_engine(DATABASE_URL)
            conn = engine.connect()
            conn.close()
            print("Base de datos lista")
            return
        except Exception:
            print("Esperando base de datos...")
            retries -= 1
            time.sleep(3)
    raise Exception("No se pudo conectar a la base de datos")

wait_for_db()

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()