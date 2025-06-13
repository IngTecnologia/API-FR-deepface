from fastapi import APIRouter, Form, UploadFile, HTTPException
from deepface import DeepFace
from datetime import datetime
import json
import shutil
import os
import uuid
from math import radians, cos, sin, sqrt, atan2
from typing import Optional
from session_tokens import generar_token, validar_token
from attendance_records import save_record
from config import (
    BASE_IMAGE_PATH, TMP_UPLOAD_PATH, UBICACIONES_FILE, USERS_FILE,
    FACE_MODEL, DETECTOR_BACKEND, DISTANCE_METRIC, ANTI_SPOOFING
)
from location import verificar_ubicacion, calcular_distancia_m
from PIL import Image

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

def verificar_ubicacion(lat, lng, ubicaciones_usuario):
    """Verifica si el usuario está dentro de alguna de sus ubicaciones.
    
    Args:
        lat: Latitud actual del usuario
        lng: Longitud actual del usuario
        ubicaciones_usuario: Lista de ubicaciones del usuario
        
    Returns:
        (bool, float, str): Tupla con (está_en_ubicación, distancia_mínima, nombre_ubicación)
    """
    if not ubicaciones_usuario:
        return False, 0, ""
    
    # Si es formato antiguo, convertir a lista
    if not isinstance(ubicaciones_usuario, list):
        if "ubicaciones" in ubicaciones_usuario:
            ubicaciones_usuario = ubicaciones_usuario["ubicaciones"]
        else:
            ubicaciones_usuario = [{
                "lat": ubicaciones_usuario.get("lat", 0),
                "lng": ubicaciones_usuario.get("lng", 0),
                "radio_metros": ubicaciones_usuario.get("radio_metros", 200),
                "nombre": "Principal"
            }]
    
    # Verificar cada ubicación
    distancia_minima = float('inf')
    nombre_ubicacion = ""
    en_ubicacion = False
    
    for ubicacion in ubicaciones_usuario:
        distancia = calcular_distancia_m(lat, lng, ubicacion["lat"], ubicacion["lng"])
        
        if distancia < distancia_minima:
            distancia_minima = distancia
            nombre_ubicacion = ubicacion["nombre"]
            
            if distancia <= ubicacion["radio_metros"]:
                en_ubicacion = True
    
    return en_ubicacion, distancia_minima, nombre_ubicacion

def rotate_image_pil(image_path, angle):
    """
    Rota una imagen usando PIL y la guarda temporalmente.
    
    Args:
        image_path: Ruta de la imagen original
        angle: Ángulo de rotación en grados (0, 90, 180, 270)
        
    Returns:
        Ruta del archivo temporal con la imagen rotada
    """
    with Image.open(image_path) as img:
        # Rotar la imagen
        if angle == 90:
            rotated = img.transpose(Image.ROTATE_270)  # PIL usa rotación inversa
        elif angle == 180:
            rotated = img.transpose(Image.ROTATE_180)
        elif angle == 270:
            rotated = img.transpose(Image.ROTATE_90)
        else:
            rotated = img  # 0 grados, sin rotación
        
        # Crear archivo temporal
        temp_path = f"{image_path}_rotated_{angle}.jpg"
        rotated.save(temp_path, "JPEG", quality=95)
        
        return temp_path

def try_face_verification_with_rotations(base_image_path, test_image_path):
    """
    Intenta la verificación facial probando múltiples rotaciones de la imagen de prueba.
    
    Args:
        base_image_path: Ruta de la imagen de referencia (sin rotar)
        test_image_path: Ruta de la imagen a verificar
        
    Returns:
        dict: Resultado de la verificación con información adicional
    """
    angles_to_try = [0, 90, 180, 270]
    results = []
    temp_files = []
    
    for angle in angles_to_try:
        print(f"Probando rotación de {angle} grados...")
        
        # Crear imagen rotada
        if angle == 0:
            rotated_path = test_image_path
        else:
            try:
                rotated_path = rotate_image_pil(test_image_path, angle)
                temp_files.append(rotated_path)
            except Exception as e:
                print(f"Error al rotar imagen {angle}°: {str(e)}")
                results.append({
                    "rotation_angle": angle,
                    "success": False,
                    "error": f"Error al rotar: {str(e)}",
                    "verified": False,
                    "distance": 1.0
                })
                continue
        
        try:
            # Intentar verificación con DeepFace
            result = DeepFace.verify(
                img1_path=base_image_path,
                img2_path=rotated_path,
                model_name=FACE_MODEL,
                detector_backend=DETECTOR_BACKEND,
                distance_metric=DISTANCE_METRIC,
                enforce_detection=False,  # Ser más permisivo
                align=True,
                anti_spoofing=ANTI_SPOOFING
            )
            
            # Agregar información de rotación al resultado
            result["rotation_angle"] = angle
            result["success"] = True
            results.append(result)
            
            print(f"Rotación {angle}°: verified={result['verified']}, distance={result['distance']:.4f}")
            
            # Si encontramos una verificación exitosa, limpiar archivos y devolver inmediatamente
            if result['verified']:
                print(f"¡Verificación exitosa con rotación de {angle} grados!")
                # Limpiar archivos temporales antes de retornar
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except Exception as e:
                        print(f"Error al eliminar archivo temporal {temp_file}: {e}")
                
                result["total_attempts"] = len(results)
                return result
                
        except Exception as e:
            print(f"Error en verificación con rotación {angle}°: {str(e)}")
            results.append({
                "rotation_angle": angle,
                "success": False,
                "error": str(e),
                "verified": False,
                "distance": 1.0
            })
    
    # Si llegamos aquí, ninguna rotación fue exitosa
    # Limpiar archivos temporales
    for temp_file in temp_files:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as e:
            print(f"Error al eliminar archivo temporal {temp_file}: {e}")
    
    # Buscar el mejor resultado entre los que no dieron error
    valid_results = [r for r in results if r.get("success", False)]
    
    if valid_results:
        # Devolver el resultado con menor distancia
        best_attempt = min(valid_results, key=lambda x: x.get("distance", 1.0))
        best_attempt["total_attempts"] = len(results)
        print(f"Ninguna rotación exitosa. Mejor intento: {best_attempt['rotation_angle']}° con distancia {best_attempt['distance']:.4f}")
        return best_attempt
    else:
        # Si todos fallaron, devolver un resultado genérico con el último error
        error_messages = [r.get("error", "") for r in results if r.get("error")]
        combined_error = "; ".join(error_messages) if error_messages else "No se pudo procesar ninguna rotación"
        
        return {
            "verified": False,
            "distance": 1.0,
            "rotation_angle": 0,
            "success": False,
            "error": combined_error,
            "total_attempts": len(results)
        }

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

    # Cargar datos de usuario para obtener el perfil
    if not os.path.exists(USERS_FILE):
        raise HTTPException(status_code=404, detail="Archivo de usuarios no encontrado")
        
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        usuarios = json.load(f)
    
    user_data = next((u for u in usuarios if u["cedula"] == cedula), None)
    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Obtener perfil de ubicación (por defecto "fijo" para mantener compatibilidad)
    perfil_ubicacion = user_data.get("perfil_ubicacion", "fijo")
    
    with open(UBICACIONES_FILE, "r", encoding="utf-8") as f:
        ubicaciones = json.load(f)

    user_ubicacion = next((u for u in ubicaciones if u["cedula"] == cedula), None)
    if not user_ubicacion:
        raise HTTPException(status_code=404, detail="No hay ubicación registrada para esta cédula")
    
    # Verificar ubicación con la función actualizada
    if "ubicaciones" in user_ubicacion:
        en_ubicacion, distancia, nombre_ubicacion = verificar_ubicacion(lat, lng, user_ubicacion["ubicaciones"])
        nombre_usuario = user_ubicacion.get("nombre_usuario", user_data.get("nombre", "Usuario"))
    else:
        # Formato antiguo
        distancia = calcular_distancia_m(lat, lng, user_ubicacion["lat"], user_ubicacion["lng"])
        en_ubicacion = distancia <= user_ubicacion.get("radio_metros", 200)
        nombre_ubicacion = "Principal"
        nombre_usuario = user_ubicacion.get("nombre", user_data.get("nombre", "Usuario"))
    
    # Variable para indicar si está fuera de su ubicación asignada
    fuera_de_ubicacion = not en_ubicacion
    
    # Comprobar según el perfil
    if perfil_ubicacion == "libre":
        # Siempre permitido, sin importar la ubicación
        token = generar_token(cedula, tipo_registro=tipo_registro)
        return {
            "valid": True,
            "nombre": nombre_usuario,
            "mensaje": "Ubicación aceptada (perfil libre)",
            "session_token": token,
            "fuera_de_ubicacion": fuera_de_ubicacion,
            "requiere_comentario": False,  # Comentario opcional
            "ubicacion_actual": nombre_ubicacion,
            "distancia": int(distancia)
        }
    
    elif perfil_ubicacion == "movil":
        # Permitido, pero se marca si está fuera de ubicación y requiere comentario
        token = generar_token(cedula, tipo_registro=tipo_registro)
        mensaje = "Ubicación aceptada" if not fuera_de_ubicacion else "Estás fuera de tu ubicación asignada (se generará reporte)"
        return {
            "valid": True,
            "nombre": nombre_usuario,
            "mensaje": mensaje,
            "session_token": token,
            "fuera_de_ubicacion": fuera_de_ubicacion,
            "requiere_comentario": fuera_de_ubicacion,  # Comentario obligatorio si está fuera
            "ubicacion_actual": nombre_ubicacion,
            "distancia": int(distancia)
        }
    
    else:  # perfil "fijo" (comportamiento original)
        if not fuera_de_ubicacion:
            token = generar_token(cedula, tipo_registro=tipo_registro)
            return {
                "valid": True,
                "nombre": nombre_usuario,
                "mensaje": "Ubicación aceptada",
                "session_token": token,
                "fuera_de_ubicacion": False,
                "requiere_comentario": False,
                "ubicacion_actual": nombre_ubicacion,
                "distancia": int(distancia)
            }
        else:
            return {
                "valid": False,
                "mensaje": f"Estás fuera del rango permitido ({int(distancia)} m)",
                "fuera_de_ubicacion": True,
                "ubicacion_actual": nombre_ubicacion,
                "distancia": int(distancia)
            }


# -------------------------------
# Paso 2: Verificar rostro con token - MODIFICADO PARA ROTACIONES
# -------------------------------
@router.post("/verify-web/face")
async def verify_web_face(
    cedula: str = Form(...),
    session_token: str = Form(...),
    image: UploadFile = Form(...),
    fuera_de_ubicacion: bool = Form(False),
    comentario: Optional[str] = Form(None)
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

        # Verificar si el comentario es requerido
        if fuera_de_ubicacion:
            # Cargar perfil del usuario
            with open(USERS_FILE, "r") as f:
                usuarios = json.load(f)
                usuario = next((u for u in usuarios if u["cedula"] == cedula), None)
            
            if usuario:
                perfil_ubicacion = usuario.get("perfil_ubicacion", "fijo")
                # Para perfil "movil", el comentario es obligatorio
                if perfil_ubicacion == "movil" and (comentario is None or comentario.strip() == ""):
                    raise HTTPException(
                        status_code=400, 
                        detail="Se requiere un comentario al registrar fuera de la ubicación asignada"
                    )

        base_path = os.path.join(IMAGENES_BASE, f"{cedula}.jpg")
        if not os.path.exists(base_path):
            raise HTTPException(status_code=404, detail=f"Imagen base no encontrada en {base_path}")

        # Generar ruta para archivo temporal
        tmp_path = os.path.join(TMP_UPLOADS, f"web_{cedula}_{datetime.utcnow().timestamp()}.jpg")
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(image.file, f)

        print(f"Iniciando verificación facial con rotaciones para cédula: {cedula}")

        # NUEVA FUNCIONALIDAD: Probar múltiples rotaciones
        result = try_face_verification_with_rotations(base_path, tmp_path)
        
        print(f"Verificación completada:")
        print(f"- Verificado: {result.get('verified', False)}")
        print(f"- Distancia: {result.get('distance', 1.0):.4f}")
        print(f"- Rotación aplicada: {result.get('rotation_angle', 0)}°")
        print(f"- Intentos totales: {result.get('total_attempts', 0)}")

        # Solo lanzar error si NO hay success en ninguna rotación Y verified es False
        if not result.get("success", False) and not result.get("verified", False):
            error_message = result.get("error", "Error en todas las rotaciones de verificación facial")
            print(f"Todas las rotaciones fallaron: {error_message}")
            # No lanzar HTTPException aquí, dejar que continúe y se registre el intento

        # Obtener empresa del usuario
        empresa = "principal"  # Valor por defecto
        ubicacion_nombre = "Sin registrar"
        
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                usuarios = json.load(f)
                usuario = next((u for u in usuarios if u["cedula"] == cedula), None)
                if usuario and "empresa" in usuario:
                    empresa = usuario["empresa"]
        
        # Obtener nombre de ubicación si es posible
        if os.path.exists(UBICACIONES_FILE):
            with open(UBICACIONES_FILE, "r") as f:
                ubicaciones = json.load(f)
                ubicacion_usuario = next((u for u in ubicaciones if u["cedula"] == cedula), None)
                if ubicacion_usuario:
                    if "ubicaciones" in ubicacion_usuario:
                        # Formato nuevo
                        for ubicacion in ubicacion_usuario["ubicaciones"]:
                            if ubicacion.get("nombre"):
                                ubicacion_nombre = ubicacion.get("nombre")
                                break
                    else:
                        # Formato antiguo
                        ubicacion_nombre = "Principal"
        
        # Crear registro para almacenar
        timestamp = datetime.utcnow().isoformat()
        record_id = str(uuid.uuid4())
        
        # Comentario con información de rotación
        comentario_final = comentario if comentario else ""
        if result.get('rotation_angle', 0) != 0:
            rotation_info = f"Rotación aplicada: {result.get('rotation_angle', 0)}°"
            comentario_final = f"{comentario_final} {rotation_info}".strip()
        
        record_data = {
            "id": record_id,
            "cedula": cedula,
            "timestamp": timestamp,
            "tipo_registro": tipo_registro,
            "verificado": result.get("verified", False),
            "distancia": result.get("distance", 1.0),
            "terminal_id": None,
            "web": True,
            "empresa": empresa,
            "fuera_de_ubicacion": fuera_de_ubicacion,
            "comentario": comentario_final,
            "ubicacion_nombre": ubicacion_nombre
        }
        
        # Guardar registro
        save_record(record_data)
        
        # Preparar respuesta
        response = {
            "record_id": record_id,
            "verified": result.get("verified", False),
            "distance": result.get("distance", 1.0),
            "cedula": cedula,
            "tipo_registro": tipo_registro,
            "timestamp": timestamp,
            "fuera_de_ubicacion": fuera_de_ubicacion,
            "comentario": comentario_final,
            "ubicacion_nombre": ubicacion_nombre,
            # Información adicional sobre rotación para debugging
            "rotation_info": {
                "angle_applied": result.get("rotation_angle", 0),
                "total_attempts": result.get("total_attempts", 1)
            }
        }
        
        # Limpiar archivo temporal antes de devolver respuesta
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                print(f"Archivo temporal eliminado: {tmp_path}")
            except Exception as e:
                print(f"No se pudo eliminar el archivo temporal: {str(e)}")
        
        return response
        
    except HTTPException:
        # Re-lanzar HTTPException específicas (como validación de token)
        raise
        
    except Exception as e:
        # Asegurarse de limpiar el archivo temporal en caso de error
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                print(f"Archivo temporal eliminado después de error: {tmp_path}")
            except Exception as clean_error:
                print(f"No se pudo eliminar el archivo temporal: {str(clean_error)}")
        
        # En lugar de HTTPException, devolver un resultado negativo
        print(f"Error general en verificación: {str(e)}")
        
        # Crear respuesta de error pero válida
        timestamp = datetime.utcnow().isoformat()
        record_id = str(uuid.uuid4())
        
        error_record = {
            "id": record_id,
            "cedula": cedula,
            "timestamp": timestamp,
            "tipo_registro": "entrada",  # valor por defecto
            "verificado": False,
            "distancia": 1.0,
            "terminal_id": None,
            "web": True,
            "empresa": "principal",
            "fuera_de_ubicacion": fuera_de_ubicacion,
            "comentario": f"Error en verificación: {str(e)}",
            "ubicacion_nombre": "Error"
        }
        
        # Intentar guardar el registro de error
        try:
            save_record(error_record)
        except Exception:
            pass  # Si no se puede guardar, continuar
        
        return {
            "record_id": record_id,
            "verified": False,
            "distance": 1.0,
            "cedula": cedula,
            "tipo_registro": "entrada",
            "timestamp": timestamp,
            "fuera_de_ubicacion": fuera_de_ubicacion,
            "comentario": f"Error en verificación: {str(e)}",
            "ubicacion_nombre": "Error",
            "rotation_info": {
                "angle_applied": 0,
                "total_attempts": 0,
                "error": str(e)
            }
        }
