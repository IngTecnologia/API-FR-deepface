from fastapi import APIRouter, UploadFile, Form, Header, HTTPException
from deepface import DeepFace
from datetime import datetime
import shutil
import os
import json
import uuid
from attendance_records import save_record
from config import (
    API_KEYS, BASE_IMAGE_PATH, TMP_UPLOAD_PATH, USERS_FILE,
    FACE_MODEL, DETECTOR_BACKEND, DISTANCE_METRIC, ANTI_SPOOFING
)

router = APIRouter()

# Asegurarse de que los directorios existan
os.makedirs(BASE_IMAGE_PATH, exist_ok=True)
os.makedirs(TMP_UPLOAD_PATH, exist_ok=True)

@router.post("/verify-terminal")
async def verify_terminal(
    cedula: str = Form(...),
    terminal_id: str = Form(...),
    tipo_registro: str = Form(...),
    image: UploadFile = Form(...),
    x_api_key: str = Header(None)
):
    # Validar tipo_registro
    if tipo_registro not in ["entrada", "salida"]:
        raise HTTPException(status_code=400, detail="tipo_registro debe ser 'entrada' o 'salida'")

    # Validar API Key
    expected_key = API_KEYS.get(terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")

    # Construir rutas absolutas
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(current_dir, BASE_IMAGE_PATH, f"{cedula}.jpg")
    
    # Nombre único para archivo temporal basado en timestamp
    tmp_filename = f"{cedula}_{datetime.utcnow().timestamp()}.jpg"
    tmp_path = os.path.join(current_dir, TMP_UPLOAD_PATH, tmp_filename)
    
    print(f"Ruta de imagen base: {base_path}")
    print(f"Ruta de imagen temporal: {tmp_path}")

    # Verificar que la imagen base existe
    if not os.path.isfile(base_path):
        print(f"Imagen base no encontrada en: {base_path}")
        # Verificar si existe en la ruta relativa
        alt_base_path = os.path.join(BASE_IMAGE_PATH, f"{cedula}.jpg")
        if os.path.isfile(alt_base_path):
            print(f"Imagen base encontrada en ruta relativa: {alt_base_path}")
            base_path = alt_base_path
        else:
            raise HTTPException(status_code=404, detail=f"Imagen base no encontrada en la ruta {base_path}")

    # Guardar imagen temporal
    try:
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        # Verificar que se guardó correctamente
        if not os.path.isfile(tmp_path):
            raise HTTPException(status_code=500, detail="Error al guardar la imagen temporal")
        
        print(f"Imagen temporal guardada correctamente: {os.path.getsize(tmp_path)} bytes")
    except Exception as e:
        print(f"Error al guardar imagen temporal: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la imagen: {str(e)}")

    try:
        # Cargar las imágenes explícitamente
        import cv2
        
        print("Cargando imágenes con OpenCV...")
        img1 = cv2.imread(base_path)
        img2 = cv2.imread(tmp_path)
        
        if img1 is None:
            print(f"OpenCV no pudo cargar la imagen base: {base_path}")
            raise HTTPException(status_code=500, detail=f"No se pudo cargar la imagen base")
        
        if img2 is None:
            print(f"OpenCV no pudo cargar la imagen temporal: {tmp_path}")
            raise HTTPException(status_code=500, detail=f"No se pudo cargar la imagen temporal")
        
        print(f"Imagen base cargada: {img1.shape}")
        print(f"Imagen temporal cargada: {img2.shape}")
        
        # Comparar con DeepFace usando objetos de imagen
        result = DeepFace.verify(
            img1_path=img1,
            img2_path=img2,
            model_name=FACE_MODEL,
            detector_backend=DETECTOR_BACKEND,
            distance_metric=DISTANCE_METRIC,
            enforce_detection=False,
            anti_spoofing=False
        )
        
        print("Verificación DeepFace completada con éxito")
        
        # Obtener empresa del usuario
        empresa = "principal"  # Valor por defecto
        
        if os.path.exists(USERS_FILE):
            try:
                with open(USERS_FILE, "r") as f:
                    usuarios = json.load(f)
                    usuario = next((u for u in usuarios if u["cedula"] == cedula), None)
                    if usuario and "empresa" in usuario:
                        empresa = usuario["empresa"]
            except Exception as e:
                print(f"Error al leer archivo de usuarios: {str(e)}")
                # Continuar con el valor por defecto

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
            "terminal_id": terminal_id,
            "web": False,
            "empresa": empresa
        }
        
        # Guardar registro
        try:
            save_record(record_data)
            print(f"Registro guardado con ID: {record_id}")
        except Exception as e:
            print(f"Error al guardar registro: {str(e)}")
            # Continuar aunque falle el guardado del registro
        
        # Preparar respuesta
        response_data = {
            "record_id": record_id,
            "verified": result["verified"],
            "distance": result["distance"],
            "cedula": cedula,
            "tipo_registro": tipo_registro,
            "timestamp": timestamp
        }
        
        # Limpiar archivo temporal después de procesar
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                print(f"Archivo temporal eliminado: {tmp_path}")
            except Exception as e:
                print(f"No se pudo eliminar el archivo temporal: {str(e)}")
        
        return response_data
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error en DeepFace: {str(e)}")
        print(error_details)
        
        # Intentar limpiar el archivo temporal incluso en caso de error
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                print(f"Archivo temporal eliminado después de error: {tmp_path}")
            except Exception as clean_error:
                print(f"No se pudo eliminar el archivo temporal: {str(clean_error)}")
        
        raise HTTPException(status_code=500, detail=f"Error en verificación facial: {str(e)}")