from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from datetime import datetime
import json
import os
from typing import List, Optional
from config import API_KEYS, USERS_FILE

router = APIRouter()

class FingerprintAssociation(BaseModel):
    """Modelo para asociar template_id con usuario"""
    cedula: str
    template_id: int
    quality_score: Optional[int] = None
    enrollment_timestamp: str

class BulkFingerprintRequest(BaseModel):
    """Modelo para asociaciones masivas de huellas"""
    terminal_id: str
    associations: List[FingerprintAssociation]

@router.post("/terminal-users/fingerprint")
async def associate_fingerprint_template(
    association: FingerprintAssociation,
    terminal_id: str,
    x_api_key: str = Header(None)
):
    """
    Asocia un template_id del sensor AS608 con un usuario.
    Crítico para el modo offline del terminal.
    """
    # Validar API Key
    expected_key = API_KEYS.get(terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")
    
    # Validar que el template_id esté en rango válido para AS608
    if not (1 <= association.template_id <= 162):
        raise HTTPException(status_code=400, detail="template_id debe estar entre 1 y 162")
    
    # Cargar usuarios existentes
    if not os.path.exists(USERS_FILE):
        raise HTTPException(status_code=404, detail="No hay usuarios registrados")
    
    with open(USERS_FILE, "r") as f:
        usuarios = json.load(f)
    
    # Buscar el usuario
    user_index = None
    for i, user in enumerate(usuarios):
        if user["cedula"] == association.cedula:
            user_index = i
            break
    
    if user_index is None:
        raise HTTPException(status_code=404, detail=f"Usuario con cédula {association.cedula} no encontrado")
    
    # Verificar que el template_id no esté ya asociado a otro usuario
    for user in usuarios:
        if user.get("fingerprint_template_id") == association.template_id and user["cedula"] != association.cedula:
            raise HTTPException(
                status_code=400, 
                detail=f"Template ID {association.template_id} ya está asociado a otro usuario"
            )
    
    # Actualizar el usuario con el template_id
    usuarios[user_index]["fingerprint_template_id"] = association.template_id
    usuarios[user_index]["fingerprint_quality"] = association.quality_score
    usuarios[user_index]["fingerprint_enrollment_date"] = association.enrollment_timestamp
    usuarios[user_index]["fingerprint_terminal_id"] = terminal_id
    usuarios[user_index]["updated_at"] = datetime.utcnow().isoformat()
    
    # Guardar cambios
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=2, ensure_ascii=False)
    
    return {
        "success": True,
        "message": f"Template ID {association.template_id} asociado correctamente",
        "user": {
            "cedula": association.cedula,
            "nombre": usuarios[user_index]["nombre"],
            "template_id": association.template_id,
            "quality_score": association.quality_score,
            "terminal_id": terminal_id
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/terminal-users/fingerprint/bulk")
async def bulk_associate_fingerprint_templates(
    bulk_request: BulkFingerprintRequest,
    x_api_key: str = Header(None)
):
    """
    Asocia múltiples template_ids con usuarios en una sola operación.
    Útil para inicialización masiva de terminales.
    """
    # Validar API Key
    expected_key = API_KEYS.get(bulk_request.terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")
    
    if not bulk_request.associations:
        raise HTTPException(status_code=400, detail="No hay asociaciones para procesar")
    
    # Cargar usuarios existentes
    if not os.path.exists(USERS_FILE):
        raise HTTPException(status_code=404, detail="No hay usuarios registrados")
    
    with open(USERS_FILE, "r") as f:
        usuarios = json.load(f)
    
    processed_associations = []
    failed_associations = []
    
    for association in bulk_request.associations:
        try:
            # Validar template_id
            if not (1 <= association.template_id <= 162):
                raise ValueError("template_id debe estar entre 1 y 162")
            
            # Buscar usuario
            user_index = None
            for i, user in enumerate(usuarios):
                if user["cedula"] == association.cedula:
                    user_index = i
                    break
            
            if user_index is None:
                raise ValueError(f"Usuario con cédula {association.cedula} no encontrado")
            
            # Verificar que template_id no esté duplicado
            for user in usuarios:
                if (user.get("fingerprint_template_id") == association.template_id and 
                    user["cedula"] != association.cedula):
                    raise ValueError(f"Template ID {association.template_id} ya está asociado")
            
            # Actualizar usuario
            usuarios[user_index]["fingerprint_template_id"] = association.template_id
            usuarios[user_index]["fingerprint_quality"] = association.quality_score
            usuarios[user_index]["fingerprint_enrollment_date"] = association.enrollment_timestamp
            usuarios[user_index]["fingerprint_terminal_id"] = bulk_request.terminal_id
            usuarios[user_index]["updated_at"] = datetime.utcnow().isoformat()
            
            processed_associations.append({
                "cedula": association.cedula,
                "template_id": association.template_id,
                "status": "success"
            })
            
        except Exception as e:
            failed_associations.append({
                "cedula": association.cedula,
                "template_id": association.template_id,
                "error": str(e),
                "status": "failed"
            })
    
    # Guardar cambios solo si hubo al menos una asociación exitosa
    if processed_associations:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(usuarios, f, indent=2, ensure_ascii=False)
    
    return {
        "terminal_id": bulk_request.terminal_id,
        "timestamp": datetime.utcnow().isoformat(),
        "summary": {
            "total_received": len(bulk_request.associations),
            "processed_successfully": len(processed_associations),
            "failed": len(failed_associations)
        },
        "processed_associations": processed_associations,
        "failed_associations": failed_associations
    }

@router.get("/terminal-users/fingerprint/{terminal_id}")
async def get_terminal_fingerprint_mappings(
    terminal_id: str,
    x_api_key: str = Header(None)
):
    """
    Obtiene todas las asociaciones template_id -> usuario para un terminal.
    Crítico para inicialización del modo offline.
    """
    # Validar API Key
    expected_key = API_KEYS.get(terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")
    
    # Cargar usuarios
    if not os.path.exists(USERS_FILE):
        return {
            "terminal_id": terminal_id,
            "mappings": [],
            "total_mappings": 0
        }
    
    with open(USERS_FILE, "r") as f:
        usuarios = json.load(f)
    
    # Filtrar usuarios con template_id asociado a este terminal
    mappings = []
    for user in usuarios:
        if (user.get("fingerprint_template_id") and 
            user.get("fingerprint_terminal_id") == terminal_id):
            mappings.append({
                "template_id": user["fingerprint_template_id"],
                "cedula": user["cedula"],
                "nombre": user["nombre"],
                "empresa": user.get("empresa", "principal"),
                "quality_score": user.get("fingerprint_quality"),
                "enrollment_date": user.get("fingerprint_enrollment_date")
            })
    
    # Ordenar por template_id para facilitar búsqueda
    mappings.sort(key=lambda x: x["template_id"])
    
    return {
        "terminal_id": terminal_id,
        "mappings": mappings,
        "total_mappings": len(mappings),
        "timestamp": datetime.utcnow().isoformat()
    }

@router.delete("/terminal-users/fingerprint/{terminal_id}/{template_id}")
async def remove_fingerprint_association(
    terminal_id: str,
    template_id: int,
    x_api_key: str = Header(None)
):
    """
    Elimina la asociación de un template_id específico.
    Útil para mantenimiento y corrección de errores.
    """
    # Validar API Key
    expected_key = API_KEYS.get(terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")
    
    # Validar template_id
    if not (1 <= template_id <= 162):
        raise HTTPException(status_code=400, detail="template_id debe estar entre 1 y 162")
    
    # Cargar usuarios
    if not os.path.exists(USERS_FILE):
        raise HTTPException(status_code=404, detail="No hay usuarios registrados")
    
    with open(USERS_FILE, "r") as f:
        usuarios = json.load(f)
    
    # Buscar usuario con este template_id
    user_found = False
    for user in usuarios:
        if (user.get("fingerprint_template_id") == template_id and 
            user.get("fingerprint_terminal_id") == terminal_id):
            # Eliminar asociación
            user.pop("fingerprint_template_id", None)
            user.pop("fingerprint_quality", None)
            user.pop("fingerprint_enrollment_date", None)
            user.pop("fingerprint_terminal_id", None)
            user["updated_at"] = datetime.utcnow().isoformat()
            user_found = True
            break
    
    if not user_found:
        raise HTTPException(
            status_code=404, 
            detail=f"No se encontró asociación para template_id {template_id} en terminal {terminal_id}"
        )
    
    # Guardar cambios
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(usuarios, f, indent=2, ensure_ascii=False)
    
    return {
        "success": True,
        "message": f"Asociación eliminada para template_id {template_id}",
        "terminal_id": terminal_id,
        "template_id": template_id,
        "timestamp": datetime.utcnow().isoformat()
    }