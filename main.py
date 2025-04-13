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