from fastapi import APIRouter, Form, UploadFile, HTTPException
from deepface import DeepFace
from datetime import datetime
import json
import shutil
import os
import uuid
from math import radians, cos, sin, sqrt, atan2
from session_tokens import generar_token, validar_token
from attendance_records import save_record
from config import (
    BASE_IMAGE_PATH, TMP_UPLOAD_PATH, UBICACIONES_FILE, USERS_FILE,
    FACE_MODEL, DETECTOR_BACKEND, DISTANCE_METRIC, ANTI_SPOOFING
)

router = APIRouter()

IMAGENES_BASE = BASE_IMAGE_PATH
TMP_UPLOADS = TMP_UPLOAD_PATH

os.makedirs(TMP_UPLOADS, exist_ok=True)

# Distancia entre dos coordenadas GPS en metros
def calcular_distancia_m(lat1, lng1, lat2, lng2):
    R = 6371000
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


# -------------------------------
# Paso 1: Validar ubicación del usuario y generar token
# -------------------------------
@router.post("/verify-web/init")
def verify_web_init(
    cedula: str = Form(...),
    lat: float = Form(...),
    lng: float = Form(...),
    tipo_registro: str = Form(...)
):
    if tipo_registro not in ["entrada", "salida"]:
        raise HTTPException(status_code=400, detail="tipo_registro debe ser 'entrada' o 'salida'")

    if not os.path.exists(UBICACIONES_FILE):
        raise HTTPException(status_code=500, detail="Archivo de ubicaciones no encontrado")

    with open(UBICACIONES_FILE, "r", encoding="utf-8") as f:
        ubicaciones = json.load(f)

    user = next((u for u in ubicaciones if u["cedula"] == cedula), None)
    if not user:
        raise HTTPException(status_code=404, detail="No hay ubicación registrada para esta cédula")

    distancia = calcular_distancia_m(lat, lng, user["lat"], user["lng"])

    if distancia <= user["radio_metros"]:
        # Usando JWT para generar el token
        token = generar_token(cedula, tipo_registro=tipo_registro)
        return {
            "valid": True,
            "nombre": user["nombre"],
            "mensaje": "Ubicación aceptada",
            "session_token": token
        }
    else:
        return {
            "valid": False,
            "mensaje": f"Estás fuera del rango permitido ({int(distancia)} m)"
        }


# -------------------------------
# Paso 2: Verificar rostro con token
# -------------------------------
@router.post("/verify-web/face")
async def verify_web_face(
    cedula: str = Form(...),
    session_token: str = Form(...),
    image: UploadFile = Form(...)
):
    # Variable para rastrear el archivo temporal
    tmp_path = None
    
    try:
        # Limpiar inputs
        if isinstance(cedula, str):
            cedula = cedula.strip().strip('"')
        if isinstance(session_token, str):
            session_token = session_token.strip().strip('"')
        
        valido, mensaje, tipo_registro = validar_token(session_token, cedula)
        if not valido:
            raise HTTPException(status_code=403, detail=mensaje)

        base_path = os.path.join(IMAGENES_BASE, f"{cedula}.jpg")
        if not os.path.exists(base_path):
            raise HTTPException(status_code=404, detail=f"Imagen base no encontrada en {base_path}")

        # Generar ruta para archivo temporal
        tmp_path = os.path.join(TMP_UPLOADS, f"web_{cedula}_{datetime.utcnow().timestamp()}.jpg")
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        # Verificar con DeepFace
        result = DeepFace.verify(
            img1_path=base_path,
            img2_path=tmp_path,
            model_name=FACE_MODEL,
            detector_backend=DETECTOR_BACKEND,
            distance_metric=DISTANCE_METRIC,
            enforce_detection=True,
            anti_spoofing=ANTI_SPOOFING
        )

        # Obtener empresa del usuario
        empresa = "principal"  # Valor por defecto
        
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                usuarios = json.load(f)
                usuario = next((u for u in usuarios if u["cedula"] == cedula), None)
                if usuario and "empresa" in usuario:
                    empresa = usuario["empresa"]
        
        # Crear registro para almacenar
        timestamp = datetime.utcnow().isoformat()
        record_id = str(uuid.uuid4())
        
        record_data = {
            "id": record_id,
            "cedula": cedula,
            "timestamp": timestamp,
            "tipo_registro": tipo_registro,
            "verificado": result["verified"],
            "distancia": result["distance"],
            "terminal_id": None,
            "web": True,
            "empresa": empresa
        }
        
        # Guardar registro
        save_record(record_data)
        
        # Preparar respuesta
        response = {
            "record_id": record_id,
            "verified": result["verified"],
            "distance": result["distance"],
            "cedula": cedula,
            "tipo_registro": tipo_registro,
            "timestamp": timestamp
        }
        
        # Limpiar archivo temporal antes de devolver respuesta
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                print(f"Archivo temporal eliminado: {tmp_path}")
            except Exception as e:
                print(f"No se pudo eliminar el archivo temporal: {str(e)}")
        
        return response
        
    except Exception as e:
        # Asegurarse de limpiar el archivo temporal en caso de error
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                print(f"Archivo temporal eliminado después de error: {tmp_path}")
            except Exception as clean_error:
                print(f"No se pudo eliminar el archivo temporal: {str(clean_error)}")
        
        # Re-lanzar la excepción
        raise HTTPException(status_code=500, detail=f"Error en DeepFace: {str(e)}")