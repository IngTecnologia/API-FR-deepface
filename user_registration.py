from fastapi import APIRouter, UploadFile, Form, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import shutil
from datetime import datetime
from config import (
    BASE_IMAGE_PATH, USERS_FILE, TERMINAL_REQUESTS_FILE, UBICACIONES_FILE
)

router = APIRouter()

# Asegurarse que los archivos existan
os.makedirs(BASE_IMAGE_PATH, exist_ok=True)

# Crear archivos JSON si no existen
for file_path in [USERS_FILE, TERMINAL_REQUESTS_FILE, UBICACIONES_FILE]:
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump([], f)

# Modelos de datos
class UserBase(BaseModel):
    cedula: str
    nombre: str
    empresa: str
    email: Optional[str] = None
    telefono: Optional[str] = None

class RegistrationRequest(BaseModel):
    user_id: str
    terminal_id: str
    estado: str = "pendiente"  # pendiente, aprobado, rechazado
    fecha_solicitud: str = datetime.utcnow().isoformat()

# Endpoint para registrar nuevo usuario con imagen
@router.post("/register-user")
async def register_user(
    cedula: str = Form(...),
    nombre: str = Form(...),
    empresa: str = Form(...),
    email: str = Form(None),
    telefono: str = Form(None),
    terminal_id: str = Form(...),
    imagen: UploadFile = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    radio_metros: int = Form(200)  # Radio predeterminado
):
    # Verificar si la cédula ya existe
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            usuarios = json.load(f)
            if any(u["cedula"] == cedula for u in usuarios):
                raise HTTPException(status_code=400, detail="Esta cédula ya está registrada")
    else:
        usuarios = []
    
    # Guardar imagen base
    imagen_path = os.path.join(BASE_IMAGE_PATH, f"{cedula}.jpg")
    with open(imagen_path, "wb") as f:
        shutil.copyfileobj(imagen.file, f)
    
    # Crear nuevo usuario
    nuevo_usuario = {
        "cedula": cedula,
        "nombre": nombre,
        "empresa": empresa,
        "email": email,
        "telefono": telefono,
        "fecha_registro": datetime.utcnow().isoformat()
    }
    
    usuarios.append(nuevo_usuario)
    
    # Guardar en archivo
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=2, ensure_ascii=False)
    
    # Registrar ubicación
    if os.path.exists(UBICACIONES_FILE):
        with open(UBICACIONES_FILE, "r") as f:
            ubicaciones = json.load(f)
    else:
        ubicaciones = []
    
    nueva_ubicacion = {
        "cedula": cedula,
        "lat": lat,
        "lng": lng,
        "radio_metros": radio_metros,
        "nombre": nombre
    }
    
    ubicaciones.append(nueva_ubicacion)
    
    with open(UBICACIONES_FILE, "w", encoding="utf-8") as f:
        json.dump(ubicaciones, f, indent=2, ensure_ascii=False)
    
    # Crear solicitud de registro para terminal
    if os.path.exists(TERMINAL_REQUESTS_FILE):
        with open(TERMINAL_REQUESTS_FILE, "r") as f:
            solicitudes = json.load(f)
    else:
        solicitudes = []
    
    nueva_solicitud = {
        "id": f"{cedula}_{terminal_id}_{datetime.utcnow().timestamp()}",
        "cedula": cedula,
        "nombre": nombre,
        "terminal_id": terminal_id,
        "estado": "pendiente",
        "fecha_solicitud": datetime.utcnow().isoformat()
    }
    
    solicitudes.append(nueva_solicitud)
    
    with open(TERMINAL_REQUESTS_FILE, "w") as f:
        json.dump(solicitudes, f, indent=2)
    
    return {
        "success": True,
        "message": "Usuario registrado correctamente. Solicitud enviada a la terminal.",
        "user_id": cedula,
        "request_id": nueva_solicitud["id"]
    }

# Endpoint para que la terminal obtenga las solicitudes pendientes
@router.get("/terminal-requests/{terminal_id}")
async def get_terminal_requests(terminal_id: str):
    if not os.path.exists(TERMINAL_REQUESTS_FILE):
        return {"requests": []}
    
    with open(TERMINAL_REQUESTS_FILE, "r") as f:
        todas_solicitudes = json.load(f)
    
    # Filtrar por terminal y estado pendiente
    solicitudes_terminal = [
        s for s in todas_solicitudes 
        if s["terminal_id"] == terminal_id and s["estado"] == "pendiente"
    ]
    
    return {"requests": solicitudes_terminal}

# Endpoint para que la terminal apruebe o rechace una solicitud
@router.post("/terminal-requests/{request_id}/update")
async def update_terminal_request(
    request_id: str,
    estado: str = Form(...)  # aprobado o rechazado
):
    if estado not in ["aprobado", "rechazado"]:
        raise HTTPException(status_code=400, detail="Estado debe ser 'aprobado' o 'rechazado'")
    
    if not os.path.exists(TERMINAL_REQUESTS_FILE):
        raise HTTPException(status_code=404, detail="No existen solicitudes")
    
    with open(TERMINAL_REQUESTS_FILE, "r") as f:
        solicitudes = json.load(f)
    
    # Buscar la solicitud
    solicitud_index = next((i for i, s in enumerate(solicitudes) if s["id"] == request_id), None)
    
    if solicitud_index is None:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    # Actualizar estado
    solicitudes[solicitud_index]["estado"] = estado
    solicitudes[solicitud_index]["fecha_actualizacion"] = datetime.utcnow().isoformat()
    
    with open(TERMINAL_REQUESTS_FILE, "w") as f:
        json.dump(solicitudes, f, indent=2)
    
    return {
        "success": True,
        "message": f"Solicitud {estado} correctamente"
    }