from fastapi import APIRouter, Header, HTTPException, Query
import json
import os
from typing import List, Optional
from datetime import datetime
from config import USERS_FILE, API_KEYS

router = APIRouter()

# Formato de base de datos optimizado para ESP32
# La idea es minimizar el tamaño del JSON enviado a la terminal
class TerminalDatabaseRecord:
    def __init__(self, cedula, nombre, empresa, slot=None):
        self.cedula = cedula
        self.nombre = nombre
        self.empresa = empresa
        self.slot = slot  # Identificador en la memoria local

def generate_terminal_database():
    """Genera la base de datos optimizada para terminales"""
    if not os.path.exists(USERS_FILE):
        return []
    
    with open(USERS_FILE, "r") as f:
        usuarios = json.load(f)
    
    # Crear registros optimizados
    terminal_records = []
    for idx, usuario in enumerate(usuarios):
        terminal_records.append({
            "c": usuario["cedula"],  # Cédula (abreviada para reducir tamaño)
            "n": usuario["nombre"][:30],  # Nombre (limitado a 30 caracteres)
            "e": usuario["empresa"],  # Empresa
            "s": idx + 1  # Slot (posición en la memoria local)
        })
    
    return terminal_records

@router.get("/terminal-sync/{terminal_id}")
async def sync_terminal_database(
    terminal_id: str,
    x_api_key: str = Header(None),
    last_sync: Optional[str] = Query(None)
):
    # Validar API Key
    expected_key = API_KEYS.get(terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")
    
    # Generar base de datos para la terminal
    db_records = generate_terminal_database()
    
    # Si hay un last_sync, podríamos filtrar solo los registros nuevos o actualizados
    # Por ahora enviamos toda la base de datos por simplicidad
    
    # Respuesta con metadatos y datos
    return {
        "sync_timestamp": datetime.utcnow().isoformat(),
        "total_records": len(db_records),
        "records": db_records
    }

@router.get("/terminal-sync/{terminal_id}/check")
async def check_sync_status(
    terminal_id: str,
    x_api_key: str = Header(None)
):
    """Endpoint para verificar si se necesita sincronizar"""
    # Validar API Key
    expected_key = API_KEYS.get(terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")
    
    # Determinar si hay cambios desde la última sincronización
    # Verificar si hay modificaciones en el archivo de usuarios
    if os.path.exists(USERS_FILE):
        last_modified = os.path.getmtime(USERS_FILE)
        last_modified_date = datetime.fromtimestamp(last_modified).isoformat()
    else:
        last_modified_date = datetime.utcnow().isoformat()
    
    # Obtener cantidad de usuarios como referencia
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            usuarios = json.load(f)
        user_count = len(usuarios)
    else:
        user_count = 0
    
    return {
        "needs_sync": True,  # Siempre recomendamos sincronizar por ahora
        "last_modified": last_modified_date,
        "user_count": user_count
    }