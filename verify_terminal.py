from fastapi import APIRouter, UploadFile, Form, Header, HTTPException
from deepface import DeepFace
from datetime import datetime
import shutil
import os
import json
import uuid
from typing import Optional
from attendance_records import save_record, detect_automatic_record_type
from config import (
    API_KEYS, BASE_IMAGE_PATH, TMP_UPLOAD_PATH, USERS_FILE, UBICACIONES_FILE,
    FACE_MODEL, DETECTOR_BACKEND, DISTANCE_METRIC, ANTI_SPOOFING
)
from location import verificar_ubicacion, calcular_distancia_m

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
    lat: Optional[float] = Form(None),  # Opcional para terminales fijas
    lng: Optional[float] = Form(None),  # Opcional para terminales fijas
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
        
        # Variables para información de ubicación
        fuera_de_ubicacion = False
        ubicacion_nombre = "Terminal"
        distancia = 0
        
        # Si tenemos datos de ubicación, verificamos según el perfil
        if lat is not None and lng is not None:
            # Cargar perfil de ubicación del usuario
            if os.path.exists(USERS_FILE):
                with open(USERS_FILE, "r") as f:
                    usuarios = json.load(f)
                    usuario = next((u for u in usuarios if u["cedula"] == cedula), None)
                    
                perfil_ubicacion = usuario.get("perfil_ubicacion", "fijo") if usuario else "fijo"
                
                # Cargar ubicaciones del usuario
                if os.path.exists(UBICACIONES_FILE):
                    with open(UBICACIONES_FILE, "r") as f:
                        ubicaciones = json.load(f)
                        usuario_ubicacion = next((u for u in ubicaciones if u["cedula"] == cedula), None)
                    
                    if usuario_ubicacion:
                        # Verificar ubicación con la función actualizada
                        if "ubicaciones" in usuario_ubicacion:
                            en_ubicacion, distancia, ubicacion_actual = verificar_ubicacion(
                                lat, lng, usuario_ubicacion["ubicaciones"]
                            )
                            ubicacion_nombre = ubicacion_actual
                        else:
                            # Formato antiguo
                            distancia = calcular_distancia_m(
                                lat, lng, usuario_ubicacion["lat"], usuario_ubicacion["lng"]
                            )
                            en_ubicacion = distancia <= usuario_ubicacion.get("radio_metros", 200)
                            ubicacion_nombre = "Principal"
                        
                        fuera_de_ubicacion = not en_ubicacion
                        
                        # Si es perfil "fijo" y está fuera de ubicación, rechazar
                        if perfil_ubicacion == "fijo" and fuera_de_ubicacion:
                            raise HTTPException(
                                status_code=403, 
                                detail=f"Estás fuera del rango permitido ({int(distancia)} m)"
                            )
        
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
            "empresa": empresa,
            "fuera_de_ubicacion": fuera_de_ubicacion,
            "comentario": "Registro desde terminal física",  # Comentario predeterminado
            "ubicacion_nombre": ubicacion_nombre,
            "distancia_ubicacion": int(distancia) if lat is not None else 0
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
            "timestamp": timestamp,
            "fuera_de_ubicacion": fuera_de_ubicacion,
            "ubicacion": ubicacion_nombre,
            "distancia_ubicacion": int(distancia) if lat is not None else 0
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

@router.post("/verify-terminal/auto")
async def verify_terminal_auto(
    terminal_id: str = Form(...),
    image: UploadFile = Form(...),
    lat: Optional[float] = Form(None),  # Opcional para terminales fijas
    lng: Optional[float] = Form(None),  # Opcional para terminales fijas
    x_api_key: str = Header(None)
):
    """
    Endpoint para verificación automática desde terminal.
    - Identifica automáticamente al usuario por la imagen
    - Detecta automáticamente si es entrada o salida
    - No requiere cédula ni tipo_registro como parámetros
    """
    
    # Validar API Key
    expected_key = API_KEYS.get(terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")

    # Construir rutas
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Nombre único para archivo temporal basado en timestamp
    tmp_filename = f"terminal_{terminal_id}_{datetime.utcnow().timestamp()}.jpg"
    tmp_path = os.path.join(current_dir, TMP_UPLOAD_PATH, tmp_filename)
    
    print(f"Procesando imagen desde terminal: {terminal_id}")
    print(f"Ruta de imagen temporal: {tmp_path}")

    # Guardar imagen temporal
    try:
        with open(tmp_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        # Verificar que se guardó correctamente
        if not os.path.isfile(tmp_path):
            raise HTTPException(status_code=500, detail="Error al guardar la imagen temporal")
        
        print(f"Imagen temporal guardada: {os.path.getsize(tmp_path)} bytes")
    except Exception as e:
        print(f"Error al guardar imagen temporal: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar la imagen: {str(e)}")

    try:
        # Cargar todos los usuarios para comparar
        if not os.path.exists(USERS_FILE):
            raise HTTPException(status_code=404, detail="No hay usuarios registrados")
        
        with open(USERS_FILE, "r") as f:
            usuarios = json.load(f)
        
        if not usuarios:
            raise HTTPException(status_code=404, detail="No hay usuarios registrados")
        
        print(f"Comparando con {len(usuarios)} usuarios registrados...")
        
        # Cargar imagen capturada
        import cv2
        img_captured = cv2.imread(tmp_path)
        
        if img_captured is None:
            raise HTTPException(status_code=500, detail="No se pudo cargar la imagen capturada")
        
        print(f"Imagen capturada cargada: {img_captured.shape}")
        
        # Buscar coincidencias con todos los usuarios
        best_match = None
        best_distance = float('inf')
        matched_user = None
        
        for usuario in usuarios:
            cedula = usuario["cedula"]
            
            # Construir ruta de imagen base del usuario
            base_path = os.path.join(current_dir, BASE_IMAGE_PATH, f"{cedula}.jpg")
            
            # Verificar que la imagen base existe
            if not os.path.isfile(base_path):
                # Intentar ruta relativa
                alt_base_path = os.path.join(BASE_IMAGE_PATH, f"{cedula}.jpg")
                if os.path.isfile(alt_base_path):
                    base_path = alt_base_path
                else:
                    print(f"Imagen base no encontrada para usuario {cedula}")
                    continue
            
            try:
                # Cargar imagen base del usuario
                img_base = cv2.imread(base_path)
                
                if img_base is None:
                    print(f"No se pudo cargar imagen base para {cedula}")
                    continue
                
                # Comparar con DeepFace
                result = DeepFace.verify(
                    img1_path=img_base,
                    img2_path=img_captured,
                    model_name=FACE_MODEL,
                    detector_backend=DETECTOR_BACKEND,
                    distance_metric=DISTANCE_METRIC,
                    enforce_detection=False,
                    anti_spoofing=ANTI_SPOOFING
                )
                
                print(f"Usuario {cedula}: verified={result['verified']}, distance={result['distance']}")
                
                # Si está verificado y es la mejor coincidencia hasta ahora
                if result["verified"] and result["distance"] < best_distance:
                    best_distance = result["distance"]
                    best_match = result
                    matched_user = usuario
                    print(f"Nueva mejor coincidencia: {cedula} con distancia {result['distance']}")
                
            except Exception as e:
                print(f"Error comparando con usuario {cedula}: {str(e)}")
                continue
        
        # Verificar si se encontró una coincidencia
        if not best_match or not matched_user:
            raise HTTPException(status_code=404, detail="Usuario no reconocido")
        
        cedula = matched_user["cedula"]
        print(f"Usuario identificado: {cedula} con confianza {best_distance}")
        
        # Detectar automáticamente el tipo de registro
        tipo_registro = detect_automatic_record_type(cedula)
        print(f"Tipo de registro detectado automáticamente: {tipo_registro}")
        
        # Variables para información de ubicación
        fuera_de_ubicacion = False
        ubicacion_nombre = "Terminal"
        distancia = 0
        
        # Si tenemos datos de ubicación, verificamos según el perfil
        if lat is not None and lng is not None:
            perfil_ubicacion = matched_user.get("perfil_ubicacion", "fijo")
            
            # Cargar ubicaciones del usuario
            if os.path.exists(UBICACIONES_FILE):
                with open(UBICACIONES_FILE, "r") as f:
                    ubicaciones = json.load(f)
                    usuario_ubicacion = next((u for u in ubicaciones if u["cedula"] == cedula), None)
                
                if usuario_ubicacion:
                    # Verificar ubicación con la función actualizada
                    if "ubicaciones" in usuario_ubicacion:
                        en_ubicacion, distancia, ubicacion_actual = verificar_ubicacion(
                            lat, lng, usuario_ubicacion["ubicaciones"]
                        )
                        ubicacion_nombre = ubicacion_actual
                    else:
                        # Formato antiguo
                        distancia = calcular_distancia_m(
                            lat, lng, usuario_ubicacion["lat"], usuario_ubicacion["lng"]
                        )
                        en_ubicacion = distancia <= usuario_ubicacion.get("radio_metros", 200)
                        ubicacion_nombre = "Principal"
                    
                    fuera_de_ubicacion = not en_ubicacion
                    
                    # Si es perfil "fijo" y está fuera de ubicación, rechazar
                    if perfil_ubicacion == "fijo" and fuera_de_ubicacion:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"Usuario {cedula} fuera del rango permitido ({int(distancia)} m)"
                        )
        
        # Obtener empresa del usuario
        empresa = matched_user.get("empresa", "principal")
        
        # Crear registro para almacenar
        timestamp = datetime.utcnow().isoformat()
        record_id = str(uuid.uuid4())
        
        record_data = {
            "id": record_id,
            "cedula": cedula,
            "timestamp": timestamp,
            "tipo_registro": tipo_registro,
            "verificado": best_match["verified"],
            "distancia": best_match["distance"],
            "terminal_id": terminal_id,
            "web": False,
            "empresa": empresa,
            "fuera_de_ubicacion": fuera_de_ubicacion,
            "comentario": "Registro automático desde terminal",
            "ubicacion_nombre": ubicacion_nombre,
            "distancia_ubicacion": int(distancia) if lat is not None else 0
        }
        
        # Guardar registro
        try:
            save_record(record_data)
            print(f"Registro automático guardado con ID: {record_id}")
        except Exception as e:
            print(f"Error al guardar registro: {str(e)}")
            # Continuar aunque falle el guardado del registro
        
        # Preparar respuesta
        response_data = {
            "record_id": record_id,
            "verified": best_match["verified"],
            "distance": best_match["distance"],
            "cedula": cedula,
            "nombre": matched_user.get("nombre", "Usuario"),
            "tipo_registro": tipo_registro,
            "timestamp": timestamp,
            "fuera_de_ubicacion": fuera_de_ubicacion,
            "ubicacion": ubicacion_nombre,
            "distancia_ubicacion": int(distancia) if lat is not None else 0,
            "mensaje": f"¡Bienvenido {matched_user.get('nombre', 'Usuario')}! Registro de {tipo_registro} exitoso."
        }
        
        # Limpiar archivo temporal después de procesar
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                print(f"Archivo temporal eliminado: {tmp_path}")
            except Exception as e:
                print(f"No se pudo eliminar el archivo temporal: {str(e)}")
        
        return response_data
        
    except HTTPException:
        # Re-lanzar HTTPExceptions sin modificar
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
        raise
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error en verificación automática: {str(e)}")
        print(error_details)
        
        # Intentar limpiar el archivo temporal incluso en caso de error
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                print(f"Archivo temporal eliminado después de error: {tmp_path}")
            except Exception as clean_error:
                print(f"No se pudo eliminar el archivo temporal: {str(clean_error)}")
        
        raise HTTPException(status_code=500, detail=f"Error en verificación automática: {str(e)}")