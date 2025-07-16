from fastapi import APIRouter, Header, HTTPException
from datetime import datetime
import json
import os
from config import API_KEYS

router = APIRouter()

@router.get("/terminal-health/{terminal_id}")
async def terminal_health_check(
    terminal_id: str,
    x_api_key: str = Header(None)
):
    """
    Health check endpoint optimizado para terminales.
    Respuesta rápida para decisión online/offline.
    """
    # Validar API Key
    expected_key = API_KEYS.get(terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")
    
    # Respuesta mínima y rápida
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "terminal_id": terminal_id,
        "api_version": "1.0.0",
        "services": {
            "facial_recognition": True,
            "database": True,
            "file_system": True
        }
    }

@router.get("/terminal-config/{terminal_id}")
async def get_terminal_config(
    terminal_id: str,
    x_api_key: str = Header(None)
):
    """
    Obtiene la configuración específica del terminal.
    """
    # Validar API Key
    expected_key = API_KEYS.get(terminal_id)
    if not expected_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="API Key inválida o terminal desconocida")
    
    # Configuración específica del terminal
    # En el futuro esto podría venir de una base de datos
    terminal_config = {
        "terminal_id": terminal_id,
        "location": {
            "name": "Oficina Principal",
            "lat": 4.6867602,
            "lng": -74.0529746,
            "radius": 200
        },
        "hardware": {
            "camera_enabled": True,
            "fingerprint_enabled": True,
            "proximity_enabled": True,
            "audio_enabled": True
        },
        "operation": {
            "mode": "hybrid",  # hybrid, online_only, offline_only
            "max_facial_attempts": 3,
            "max_fingerprint_attempts": 3,
            "timeout_seconds": 30,
            "auto_sync_interval": 300  # 5 minutos
        },
        "display": {
            "brightness": 80,
            "timeout_seconds": 60,
            "language": "es"
        },
        "sync": {
            "batch_size": 50,
            "retry_attempts": 5,
            "retry_delay_seconds": 30
        }
    }
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "config": terminal_config
    }