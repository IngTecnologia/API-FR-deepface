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
    fuera_de_ubicacion: bool = False  # Indica si está fuera de su ubicación asignada
    comentario: str = ""  # Comentario para registros fuera de ubicación
    ubicacion_nombre: str = "Principal"  # Nombre de la ubicación registrada
    distancia_ubicacion: int = 0  # Distancia a la ubicación más cercana (en metros)

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

# Endpoint para obtener todos los registros con múltiples filtros
@router.get("/records")
async def get_all_records(
    cedula: Optional[str] = None,
    empresa: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    tipo_registro: Optional[str] = None,
    fuera_de_ubicacion: Optional[bool] = None,
    perfil: Optional[str] = None
):
    """Obtiene registros con varios filtros."""
    if not os.path.exists(RECORDS_FILE):
        return {"records": []}
    
    with open(RECORDS_FILE, "r") as f:
        all_records = json.load(f)
    
    # Convertir fechas si se proporcionan
    fecha_desde = None
    fecha_hasta = None
    
    if desde:
        try:
            fecha_desde = datetime.fromisoformat(desde.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha 'desde' inválido. Use formato ISO: YYYY-MM-DD")
    
    if hasta:
        try:
            fecha_hasta = datetime.fromisoformat(hasta.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha 'hasta' inválido. Use formato ISO: YYYY-MM-DD")
    
    # Aplicar filtros
    filtered_records = all_records
    
    # Filtrar por cédula
    if cedula:
        filtered_records = [r for r in filtered_records if r["cedula"] == cedula]
    
    # Filtrar por empresa
    if empresa:
        filtered_records = [r for r in filtered_records if r.get("empresa") == empresa]
    
    # Filtrar por tipo de registro
    if tipo_registro:
        filtered_records = [r for r in filtered_records if r.get("tipo_registro") == tipo_registro]
    
    # Filtrar por estado de ubicación
    if fuera_de_ubicacion is not None:
        filtered_records = [r for r in filtered_records if r.get("fuera_de_ubicacion", False) == fuera_de_ubicacion]
    
    # Filtrar por fecha desde
    if fecha_desde:
        filtered_records = [
            r for r in filtered_records 
            if datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) >= fecha_desde
        ]
    
    # Filtrar por fecha hasta
    if fecha_hasta:
        filtered_records = [
            r for r in filtered_records 
            if datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) <= fecha_hasta
        ]
    
    # Filtrar por perfil de usuario
    if perfil:
        # Para este filtro necesitamos cargar los usuarios
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r") as f:
                usuarios = json.load(f)
            
            # Crear un diccionario de perfiles para búsqueda rápida
            perfiles = {u["cedula"]: u.get("perfil_ubicacion", "fijo") for u in usuarios}
            
            # Filtrar registros por perfil
            filtered_records = [
                r for r in filtered_records 
                if perfiles.get(r["cedula"], "fijo") == perfil
            ]
    
    return {"records": filtered_records}

# Endpoint para obtener registros fuera de ubicación
@router.get("/records/out-of-location")
async def get_out_of_location_records(
    empresa: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None
):
    """Obtiene registros realizados fuera de la ubicación asignada."""
    if not os.path.exists(RECORDS_FILE):
        return {"records": []}
    
    with open(RECORDS_FILE, "r") as f:
        all_records = json.load(f)
    
    # Convertir fechas si se proporcionan
    fecha_desde = None
    fecha_hasta = None
    
    if desde:
        try:
            fecha_desde = datetime.fromisoformat(desde.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha 'desde' inválido. Use formato ISO: YYYY-MM-DD")
    
    if hasta:
        try:
            fecha_hasta = datetime.fromisoformat(hasta.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha 'hasta' inválido. Use formato ISO: YYYY-MM-DD")
    
    # Filtrar registros
    filtered_records = all_records
    
    # Filtrar por fuera de ubicación
    filtered_records = [r for r in filtered_records if r.get("fuera_de_ubicacion", False)]
    
    # Filtrar por empresa si se especifica
    if empresa:
        filtered_records = [r for r in filtered_records if r.get("empresa") == empresa]
    
    # Filtrar por fecha desde
    if fecha_desde:
        filtered_records = [
            r for r in filtered_records 
            if datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) >= fecha_desde
        ]
    
    # Filtrar por fecha hasta
    if fecha_hasta:
        filtered_records = [
            r for r in filtered_records 
            if datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) <= fecha_hasta
        ]
    
    return {"records": filtered_records}

# Endpoint para obtener estadísticas de registros fuera de ubicación
@router.get("/statistics/out-of-location")
async def get_out_of_location_statistics(
    empresa: Optional[str] = None,
    desde: Optional[str] = None,
    hasta: Optional[str] = None
):
    """Obtiene estadísticas de registros fuera de ubicación."""
    if not os.path.exists(RECORDS_FILE):
        return {"statistics": {}}
    
    with open(RECORDS_FILE, "r") as f:
        all_records = json.load(f)
    
    # Aplicar filtros (similar al endpoint get_all_records)
    fecha_desde = None
    fecha_hasta = None
    
    if desde:
        try:
            fecha_desde = datetime.fromisoformat(desde.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha 'desde' inválido. Use formato ISO: YYYY-MM-DD")
    
    if hasta:
        try:
            fecha_hasta = datetime.fromisoformat(hasta.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha 'hasta' inválido. Use formato ISO: YYYY-MM-DD")
    
    # Filtrar registros
    filtered_records = all_records
    
    # Filtrar por empresa
    if empresa:
        filtered_records = [r for r in filtered_records if r.get("empresa") == empresa]
    
    # Filtrar por fecha desde
    if fecha_desde:
        filtered_records = [
            r for r in filtered_records 
            if datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) >= fecha_desde
        ]
    
    # Filtrar por fecha hasta
    if fecha_hasta:
        filtered_records = [
            r for r in filtered_records 
            if datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) <= fecha_hasta
        ]
    
    # Cargar usuarios para obtener perfiles
    usuarios_por_cedula = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            usuarios = json.load(f)
        
        for usuario in usuarios:
            usuarios_por_cedula[usuario["cedula"]] = usuario
    
    # Generar estadísticas
    total_registros = len(filtered_records)
    registros_fuera = len([r for r in filtered_records if r.get("fuera_de_ubicacion", False)])
    
    # Estadísticas por perfil
    stats_por_perfil = {
        "libre": 0,
        "movil": 0,
        "fijo": 0
    }
    
    for registro in filtered_records:
        if registro.get("fuera_de_ubicacion", False):
            cedula = registro["cedula"]
            perfil = "fijo"  # Por defecto
            
            if cedula in usuarios_por_cedula:
                perfil = usuarios_por_cedula[cedula].get("perfil_ubicacion", "fijo")
            
            stats_por_perfil[perfil] += 1
    
    # Estadísticas por día
    stats_por_dia = {}
    for registro in filtered_records:
        if registro.get("fuera_de_ubicacion", False):
            fecha = registro["timestamp"].split('T')[0]  # Obtener solo la fecha
            stats_por_dia[fecha] = stats_por_dia.get(fecha, 0) + 1
    
    # Estadísticas por usuario (top 10)
    stats_por_usuario = {}
    for registro in filtered_records:
        if registro.get("fuera_de_ubicacion", False):
            cedula = registro["cedula"]
            nombre = "Usuario"
            
            if cedula in usuarios_por_cedula:
                nombre = usuarios_por_cedula[cedula].get("nombre", "Usuario")
            
            key = f"{cedula} - {nombre}"
            stats_por_usuario[key] = stats_por_usuario.get(key, 0) + 1
    
    # Obtener los 10 usuarios con más registros fuera de ubicación
    top_usuarios = sorted(stats_por_usuario.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "statistics": {
            "total_registros": total_registros,
            "registros_fuera_ubicacion": registros_fuera,
            "porcentaje_fuera": round(registros_fuera / total_registros * 100, 2) if total_registros > 0 else 0,
            "por_perfil": stats_por_perfil,
            "por_dia": stats_por_dia,
            "top_usuarios": dict(top_usuarios)
        }
    }