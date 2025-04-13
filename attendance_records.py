from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import json
import os
from typing import List, Optional
from config import RECORDS_FILE, USERS_FILE

router = APIRouter()

# Crear archivo JSON si no existe
if not os.path.exists(RECORDS_FILE):
    with open(RECORDS_FILE, "w") as f:
        json.dump([], f)

# Modelos de datos
class Record(BaseModel):
    id: str
    cedula: str
    timestamp: str
    tipo_registro: str  # entrada o salida
    verificado: bool
    distancia: float
    terminal_id: Optional[str] = None  # Para registros desde terminal física
    web: bool = False  # Para diferenciar si fue desde web o terminal
    empresa: str  # Identificador de la empresa

# Guardar un nuevo registro
def save_record(record_data):
    if os.path.exists(RECORDS_FILE):
        with open(RECORDS_FILE, "r") as f:
            records = json.load(f)
    else:
        records = []
    
    records.append(record_data)
    
    with open(RECORDS_FILE, "w") as f:
        json.dump(records, f, indent=2)
    
    return record_data

# Endpoint para obtener registros por empresa
@router.get("/records/company/{empresa}")
async def get_records_by_company(empresa: str):
    # Método 1: Buscar por campo empresa directo en registros
    if not os.path.exists(RECORDS_FILE):
        return {"records": []}
    
    with open(RECORDS_FILE, "r") as f:
        all_records = json.load(f)
    
    # Filtrar por empresa directamente en los registros
    company_records = [r for r in all_records if r.get("empresa") == empresa]
    
    # Si no se encontraron registros, intentar el método alternativo por usuarios
    if not company_records:
        # Método 2: Buscar por usuarios de la empresa (compatibilidad)
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                usuarios = json.load(f)
            
            # Obtener cédulas de usuarios de la empresa
            cedulas_empresa = [u["cedula"] for u in usuarios if u.get("empresa") == empresa]
            
            if cedulas_empresa:
                # Filtrar por cédulas de la empresa
                company_records = [r for r in all_records if r["cedula"] in cedulas_empresa]
    
    return {"records": company_records}

# Endpoint para obtener registros de un usuario
@router.get("/records/{cedula}")
async def get_user_records(cedula: str):
    if not os.path.exists(RECORDS_FILE):
        return {"records": []}
    
    with open(RECORDS_FILE, "r") as f:
        all_records = json.load(f)
    
    # Filtrar por cédula
    user_records = [r for r in all_records if r["cedula"] == cedula]
    
    return {"records": user_records}

# Endpoint para obtener registros por fecha
@router.get("/records/date/{fecha}")
async def get_records_by_date(fecha: str):
    if not os.path.exists(RECORDS_FILE):
        return {"records": []}
    
    try:
        fecha_dt = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use ISO format: YYYY-MM-DD")
    
    fecha_str = fecha_dt.strftime("%Y-%m-%d")
    
    with open(RECORDS_FILE, "r") as f:
        all_records = json.load(f)
    
    # Filtrar por fecha
    date_records = [
        r for r in all_records 
        if r["timestamp"].split("T")[0] == fecha_str
    ]
    
    return {"records": date_records}

# Endpoint para obtener registros por empresa
@router.get("/records/company/{empresa}")
async def get_records_by_company(empresa: str):
    # Primero obtenemos todos los usuarios de la empresa
    if not os.path.exists(USERS_FILE):
        return {"records": []}
    
    with open(USERS_FILE, "r") as f:
        usuarios = json.load(f)
    
    # Obtener cédulas de usuarios de la empresa
    cedulas_empresa = [u["cedula"] for u in usuarios if u["empresa"] == empresa]
    
    if not cedulas_empresa:
        return {"records": []}
    
    # Obtener registros
    if not os.path.exists(RECORDS_FILE):
        return {"records": []}
    
    with open(RECORDS_FILE, "r") as f:
        all_records = json.load(f)
    
    # Filtrar por cédulas de la empresa
    company_records = [r for r in all_records if r["cedula"] in cedulas_empresa]
    
    return {"records": company_records}