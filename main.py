from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from verify_terminal import router as terminal_router
from verify_web import router as web_router
from user_registration import router as registration_router
from attendance_records import router as records_router
from terminal_sync import router as sync_router

app = FastAPI(title="DeepFace API", 
              description="API para verificación facial y control de acceso",
              version="1.0.0")

# Configurar CORS para permitir peticiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringe a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir todos los routers
app.include_router(terminal_router, tags=["Terminal Verification"])
app.include_router(web_router, tags=["Web Verification"])
app.include_router(registration_router, tags=["User Registration"])
app.include_router(records_router, tags=["Attendance Records"])
app.include_router(sync_router, tags=["Terminal Synchronization"])

@app.get("/")
def read_root():
    return {
        "message": "DeepFace API está funcionando",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/version")
def get_version():
    """Endpoint para verificar la versión actual de la aplicación."""
    return {
        "latest_version": "1.0.0",  # Cambiar cuando haya nuevas versiones
        "minimum_version": "1.0.0",  # Versión mínima soportada
        "force_update": False,  # Cambiar a True cuando se requiera actualización obligatoria
        "update_message": "Nueva versión disponible con mejoras de seguridad.",
        "download_url": "https://example.com/download"  # URL de descarga opcional
    }
