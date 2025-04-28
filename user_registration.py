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
    perfil_ubicacion: str = Form("fijo"),  # por defecto es fijo
    terminal_id: str = Form(...),
    imagen: UploadFile = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    radio_metros: int = Form(200),  # Radio predeterminado
    ubicacion_nombre: str = Form("Principal")  # Nombre descriptivo de la ubicación
):
    # Validar perfil_ubicacion
    if perfil_ubicacion not in ["libre", "movil", "fijo"]:
        raise HTTPException(status_code=400, detail="Perfil de ubicación debe ser 'libre', 'movil' o 'fijo'")
    
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
        "perfil_ubicacion": perfil_ubicacion,
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
    
    # Buscar si el usuario ya tiene ubicaciones registradas
    usuario_existente = next((i for i, u in enumerate(ubicaciones) if u["cedula"] == cedula), None)
    
    nueva_ubicacion = {
        "lat": lat,
        "lng": lng,
        "radio_metros": radio_metros,
        "nombre": ubicacion_nombre
    }
    
    if usuario_existente is not None:
        # Si ya existe, agregar la ubicación a la lista de ubicaciones
        if "ubicaciones" in ubicaciones[usuario_existente]:
            ubicaciones[usuario_existente]["ubicaciones"].append(nueva_ubicacion)
        else:
            # Migrar formato antiguo a nuevo formato
            ubicaciones[usuario_existente] = {
                "cedula": cedula,
                "nombre_usuario": nombre,
                "ubicaciones": [
                    {
                        "lat": ubicaciones[usuario_existente].get("lat", lat),
                        "lng": ubicaciones[usuario_existente].get("lng", lng),
                        "radio_metros": ubicaciones[usuario_existente].get("radio_metros", radio_metros),
                        "nombre": "Principal"
                    },
                    nueva_ubicacion
                ]
            }
    else:
        # Si no existe, crear nueva entrada
        ubicaciones.append({
            "cedula": cedula,
            "nombre_usuario": nombre,
            "ubicaciones": [nueva_ubicacion]
        })
    
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
        "request_id": nueva_solicitud["id"],
        "perfil_ubicacion": perfil_ubicacion
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

#Endpoint para añadir ubicaciones de usuario 
@router.post("/user-locations/{cedula}")
async def add_user_location(
    cedula: str,
    lat: float = Form(...),
    lng: float = Form(...),
    radio_metros: int = Form(200),
    nombre: str = Form(...)
):
    """Añade una nueva ubicación para un usuario."""
    if not os.path.exists(UBICACIONES_FILE):
        raise HTTPException(status_code=404, detail="Archivo de ubicaciones no encontrado")
    
    with open(UBICACIONES_FILE, "r") as f:
        ubicaciones = json.load(f)
    
    # Buscar usuario
    usuario_idx = next((i for i, u in enumerate(ubicaciones) if u["cedula"] == cedula), None)
    
    if usuario_idx is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    nueva_ubicacion = {
        "lat": lat,
        "lng": lng,
        "radio_metros": radio_metros,
        "nombre": nombre
    }
    
    # Verificar si tiene el nuevo formato
    if "ubicaciones" in ubicaciones[usuario_idx]:
        ubicaciones[usuario_idx]["ubicaciones"].append(nueva_ubicacion)
    else:
        # Migrar a nuevo formato
        nombre_usuario = ubicaciones[usuario_idx].get("nombre", "Usuario")
        ubicaciones[usuario_idx] = {
            "cedula": cedula,
            "nombre_usuario": nombre_usuario,
            "ubicaciones": [
                {
                    "lat": ubicaciones[usuario_idx].get("lat", 0),
                    "lng": ubicaciones[usuario_idx].get("lng", 0),
                    "radio_metros": ubicaciones[usuario_idx].get("radio_metros", 200),
                    "nombre": "Principal"
                },
                nueva_ubicacion
            ]
        }
    
    with open(UBICACIONES_FILE, "w", encoding="utf-8") as f:
        json.dump(ubicaciones, f, indent=2, ensure_ascii=False)
    
    return {"success": True, "message": "Ubicación añadida correctamente"}

#Endpoint para obtener las ubicaciones de usuario 
@router.get("/user-locations/{cedula}")
async def get_user_locations(cedula: str):
    """Obtiene todas las ubicaciones de un usuario."""
    if not os.path.exists(UBICACIONES_FILE):
        raise HTTPException(status_code=404, detail="Archivo de ubicaciones no encontrado")
    
    with open(UBICACIONES_FILE, "r") as f:
        ubicaciones = json.load(f)
    
    # Buscar usuario
    usuario = next((u for u in ubicaciones if u["cedula"] == cedula), None)
    
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Verificar formato y devolver las ubicaciones
    if "ubicaciones" in usuario:
        return {"cedula": cedula, "ubicaciones": usuario["ubicaciones"]}
    else:
        # Formato antiguo, devolver una sola ubicación
        return {
            "cedula": cedula, 
            "ubicaciones": [{
                "lat": usuario.get("lat", 0),
                "lng": usuario.get("lng", 0),
                "radio_metros": usuario.get("radio_metros", 200),
                "nombre": "Principal"
            }]
        }

#Endpoint para eliminar ubicaciones de usuario 
@router.delete("/user-locations/{cedula}/{ubicacion_idx}")
async def delete_user_location(cedula: str, ubicacion_idx: int):
    """Elimina una ubicación específica de un usuario."""
    if not os.path.exists(UBICACIONES_FILE):
        raise HTTPException(status_code=404, detail="Archivo de ubicaciones no encontrado")
    
    with open(UBICACIONES_FILE, "r") as f:
        ubicaciones = json.load(f)
    
    # Buscar usuario
    usuario_idx = next((i for i, u in enumerate(ubicaciones) if u["cedula"] == cedula), None)
    
    if usuario_idx is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Verificar formato
    if "ubicaciones" in ubicaciones[usuario_idx]:
        if ubicacion_idx < 0 or ubicacion_idx >= len(ubicaciones[usuario_idx]["ubicaciones"]):
            raise HTTPException(status_code=400, detail="Índice de ubicación inválido")
        
        # No permitir eliminar la última ubicación
        if len(ubicaciones[usuario_idx]["ubicaciones"]) <= 1:
            raise HTTPException(status_code=400, detail="No se puede eliminar la única ubicación")
        
        # Eliminar ubicación
        ubicaciones[usuario_idx]["ubicaciones"].pop(ubicacion_idx)
        
        with open(UBICACIONES_FILE, "w", encoding="utf-8") as f:
            json.dump(ubicaciones, f, indent=2, ensure_ascii=False)
        
        return {"success": True, "message": "Ubicación eliminada correctamente"}
    else:
        raise HTTPException(status_code=400, detail="Usuario con formato antiguo de ubicaciones")
    
 #Endpoint para aactualizar perfil de ubicaciones de usuario 
@router.put("/user-profile/{cedula}")
async def update_user_profile(
    cedula: str,
    perfil_ubicacion: str = Form(...)
):
    """Actualiza el perfil de ubicación de un usuario."""
    # Validar perfil_ubicacion
    if perfil_ubicacion not in ["libre", "movil", "fijo"]:
        raise HTTPException(status_code=400, detail="Perfil de ubicación debe ser 'libre', 'movil' o 'fijo'")
    
    if not os.path.exists(USERS_FILE):
        raise HTTPException(status_code=404, detail="Archivo de usuarios no encontrado")
    
    with open(USERS_FILE, "r") as f:
        usuarios = json.load(f)
    
    # Buscar el usuario
    usuario_idx = next((i for i, u in enumerate(usuarios) if u["cedula"] == cedula), None)
    
    if usuario_idx is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Actualizar perfil
    usuarios[usuario_idx]["perfil_ubicacion"] = perfil_ubicacion
    
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=2, ensure_ascii=False)
    
    return {
        "success": True,
        "message": f"Perfil de ubicación actualizado a '{perfil_ubicacion}'",
        "usuario": usuarios[usuario_idx]
    }

#Endpoint apara obtener el perfil de ubicaciones de un usuario 
@router.get("/user-profile/{cedula}")
async def get_user_profile(cedula: str):
    """Obtiene el perfil completo de un usuario."""
    if not os.path.exists(USERS_FILE):
        raise HTTPException(status_code=404, detail="Archivo de usuarios no encontrado")
    
    with open(USERS_FILE, "r") as f:
        usuarios = json.load(f)
    
    # Buscar el usuario
    usuario = next((u for u in usuarios if u["cedula"] == cedula), None)
    
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Obtener ubicaciones
    if os.path.exists(UBICACIONES_FILE):
        with open(UBICACIONES_FILE, "r") as f:
            ubicaciones = json.load(f)
        
        usuario_ubicacion = next((u for u in ubicaciones if u["cedula"] == cedula), None)
        
        if usuario_ubicacion:
            if "ubicaciones" in usuario_ubicacion:
                usuario["ubicaciones"] = usuario_ubicacion["ubicaciones"]
            else:
                # Formato antiguo
                usuario["ubicaciones"] = [{
                    "lat": usuario_ubicacion.get("lat", 0),
                    "lng": usuario_ubicacion.get("lng", 0),
                    "radio_metros": usuario_ubicacion.get("radio_metros", 200),
                    "nombre": "Principal"
                }]
    
    return usuario