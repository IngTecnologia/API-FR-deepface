import os
from typing import Dict

# Configuración de JWT
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "clave_segura_para_desarrollo")
JWT_EXPIRACION_MINUTOS = 7

# Configuración Multi-empresa
DEFAULT_EMPRESA = "principal"  # Empresa por defecto

# Configuración de API keys para terminales
API_KEYS: Dict[str, str] = {
    "TERMINAL_001": "terminal_key_001",
    "TERMINAL_002": os.environ.get("API_KEY_002", "otra_clave_segura_002")
}

# Rutas de archivos
BASE_IMAGE_PATH = "imagenes_base"
TMP_UPLOAD_PATH = "tmp_uploads"
USERS_FILE = "data/usuarios.json"
TERMINAL_REQUESTS_FILE = "data/solicitudes_registro.json"
UBICACIONES_FILE = "data/ubicaciones.json"
RECORDS_FILE = "data/registros.json"

# Configuración de DeepFace
FACE_MODEL = "SFace"  # Modelo a usar
DETECTOR_BACKEND = "opencv"  # Backend para detección
DISTANCE_METRIC = "cosine"  # Métrica de distancia
ANTI_SPOOFING = True  # Habilitar anti-spoofing