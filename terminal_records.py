from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from datetime import datetime
import json
import os
import uuid
from typing import List, Optional
from config import API_KEYS, RECORDS_FILE
from attendance_records import save_record

router = APIRouter()

class BulkRecord(BaseModel):
    """Modelo para registros individuales en el bulk upload"""
    user_id: Optional[int] = None
    cedula: str
    employee_name: str
    access_timestamp: str
    method: str  # 'online' | 'offline'
    verification_type: str  # 'facial' | 'fingerprint' | 'manual'
    confidence_score: Optional[float] = None
    device_id: str
    location_name: Optional[str] = None
    terminal_record_id: str  # ID único del terminal
    created_at: str

class BulkRecordsRequest(BaseModel):
    """Modelo para el bulk upload de registros"""
    terminal_id: str
    records: List[BulkRecord]
    sync_timestamp: str

@router.post("/terminal-records/bulk")
async def upload_bulk_records(
    bulk_request: BulkRecordsRequest,
    x_api_key: str = Header(None)
):
    """
    Endpoint para subir múltiples registros de acceso desde terminales.
    Optimizado para sincronización batch de registros offline.
    """
    # Validar API Key
    expected_key = API_KEYS.get(bulk_request.terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")
    
    if not bulk_request.records:
        raise HTTPException(status_code=400, detail="No hay registros para procesar")
    
    # Procesar cada registro
    processed_records = []
    failed_records = []
    
    for record in bulk_request.records:
        try:
            # Generar ID único para el servidor
            server_record_id = str(uuid.uuid4())
            
            # Convertir el registro del terminal al formato del servidor
            server_record = {
                "id": server_record_id,
                "cedula": record.cedula,
                "timestamp": record.access_timestamp,
                "tipo_registro": _detect_record_type(record.cedula, record.access_timestamp),
                "verificado": record.verification_type != "manual",  # Manual entries are not verified
                "distancia": record.confidence_score or 0.0,
                "terminal_id": bulk_request.terminal_id,
                "web": False,
                "empresa": "principal",  # Default empresa
                "fuera_de_ubicacion": False,  # Asumimos que terminales están en ubicación correcta
                "comentario": f"Registro {record.verification_type} desde terminal",
                "ubicacion_nombre": record.location_name or "Terminal",
                "distancia_ubicacion": 0,
                # Campos adicionales para auditoría
                "sync_timestamp": bulk_request.sync_timestamp,
                "terminal_record_id": record.terminal_record_id,
                "method": record.method,
                "verification_type": record.verification_type,
                "confidence_score": record.confidence_score,
                "created_at": record.created_at
            }
            
            # Guardar registro usando la función existente
            save_record(server_record)
            
            processed_records.append({
                "terminal_record_id": record.terminal_record_id,
                "server_record_id": server_record_id,
                "status": "success"
            })
            
        except Exception as e:
            failed_records.append({
                "terminal_record_id": record.terminal_record_id,
                "error": str(e),
                "status": "failed"
            })
    
    # Respuesta con resumen del procesamiento
    return {
        "sync_timestamp": datetime.utcnow().isoformat(),
        "terminal_id": bulk_request.terminal_id,
        "summary": {
            "total_received": len(bulk_request.records),
            "processed_successfully": len(processed_records),
            "failed": len(failed_records)
        },
        "processed_records": processed_records,
        "failed_records": failed_records
    }

def _detect_record_type(cedula: str, timestamp: str) -> str:
    """
    Detecta automáticamente si es entrada o salida basado en el último registro.
    Lógica simplificada para terminales.
    """
    # Importar aquí para evitar import circular
    from attendance_records import get_last_record
    
    try:
        last_record = get_last_record(cedula)
        if last_record and last_record.get("tipo_registro") == "entrada":
            return "salida"
        else:
            return "entrada"
    except:
        # En caso de error, default a entrada
        return "entrada"

@router.get("/terminal-records/status/{terminal_id}")
async def get_terminal_records_status(
    terminal_id: str,
    x_api_key: str = Header(None)
):
    """
    Obtiene estadísticas de registros para un terminal específico.
    Útil para monitoreo y debugging.
    """
    # Validar API Key
    expected_key = API_KEYS.get(terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")
    
    # Leer registros desde el archivo
    if not os.path.exists(RECORDS_FILE):
        return {
            "terminal_id": terminal_id,
            "total_records": 0,
            "records_today": 0,
            "last_sync": None
        }
    
    with open(RECORDS_FILE, "r") as f:
        all_records = json.load(f)
    
    # Filtrar registros de este terminal
    terminal_records = [r for r in all_records if r.get("terminal_id") == terminal_id]
    
    # Contar registros de hoy
    today = datetime.now().date()
    today_records = [
        r for r in terminal_records 
        if datetime.fromisoformat(r["timestamp"]).date() == today
    ]
    
    # Último sync
    last_sync = None
    if terminal_records:
        last_record = max(terminal_records, key=lambda x: x.get("sync_timestamp", x["timestamp"]))
        last_sync = last_record.get("sync_timestamp", last_record["timestamp"])
    
    return {
        "terminal_id": terminal_id,
        "total_records": len(terminal_records),
        "records_today": len(today_records),
        "last_sync": last_sync,
        "timestamp": datetime.utcnow().isoformat()
    }