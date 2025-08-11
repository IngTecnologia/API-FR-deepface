import json
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
import bcrypt
from config import JWT_SECRET_KEY, JWT_EXPIRACION_MINUTOS

router = APIRouter()
security = HTTPBearer()

# Archivo para usuarios admin
ADMIN_USERS_FILE = "data/admin_users.json"

# Asegurar que existe el directorio data
os.makedirs("data", exist_ok=True)

# Modelos
class AdminLogin(BaseModel):
    email: str
    password: str

class AdminUser(BaseModel):
    id: str
    email: str
    nombre: str
    empresa: str
    rol: str = "admin"
    permisos: list = []
    activo: bool = True
    fecha_creacion: str
    ultimo_acceso: Optional[str] = None

class LoginResponse(BaseModel):
    user: AdminUser
    token: str
    refreshToken: str
    expiresIn: int

# Crear usuarios admin por defecto si no existen
def init_admin_users():
    if not os.path.exists(ADMIN_USERS_FILE):
        # Crear usuario admin por defecto
        default_admin = {
            "id": "admin_001",
            "email": "admin@bioentry.com",
            "nombre": "Administrador",
            "empresa": "INEMEC",
            "rol": "super_admin",
            "permisos": [
                "dashboard.view",
                "users.view", "users.create", "users.edit", "users.delete", "users.import",
                "attendance.view", "attendance.monitor",
                "companies.view", "companies.create", "companies.edit", "companies.delete",
                "terminals.view", "terminals.config", "terminals.monitor",
                "reports.view", "reports.create", "reports.manage",
                "settings.view", "settings.admin", "settings.logs", "settings.backup"
            ],
            "activo": True,
            "fecha_creacion": datetime.utcnow().isoformat(),
            "ultimo_acceso": None,
            # Password: admin123 (hasheado con bcrypt)
            "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBdXzgVaj8l4L2"
        }
        
        with open(ADMIN_USERS_FILE, "w") as f:
            json.dump([default_admin], f, indent=2)
    
    return True

# Verificar password
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# Crear token JWT
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRACION_MINUTOS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm="HS256")
    return encoded_jwt

# Verificar token JWT
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Obtener usuario admin por email
def get_admin_user(email: str) -> Optional[dict]:
    if not os.path.exists(ADMIN_USERS_FILE):
        init_admin_users()
    
    with open(ADMIN_USERS_FILE, "r") as f:
        users = json.load(f)
    
    for user in users:
        if user["email"] == email and user["activo"]:
            return user
    return None

# Actualizar último acceso
def update_last_access(email: str):
    if not os.path.exists(ADMIN_USERS_FILE):
        return
    
    with open(ADMIN_USERS_FILE, "r") as f:
        users = json.load(f)
    
    for user in users:
        if user["email"] == email:
            user["ultimo_acceso"] = datetime.utcnow().isoformat()
            break
    
    with open(ADMIN_USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

# Endpoints
@router.post("/admin/auth/login", response_model=LoginResponse)
async def admin_login(credentials: AdminLogin):
    """Login de administrador"""
    init_admin_users()  # Asegurar que existen usuarios admin
    
    user_data = get_admin_user(credentials.email)
    if not user_data or not verify_password(credentials.password, user_data["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    
    # Actualizar último acceso
    update_last_access(credentials.email)
    
    # Crear token
    access_token_expires = timedelta(minutes=JWT_EXPIRACION_MINUTOS)
    access_token = create_access_token(
        data={
            "sub": user_data["email"],
            "user_id": user_data["id"],
            "rol": user_data["rol"],
            "empresa": user_data["empresa"]
        },
        expires_delta=access_token_expires
    )
    
    # Crear refresh token (válido por más tiempo)
    refresh_token = create_access_token(
        data={"sub": user_data["email"], "refresh": True},
        expires_delta=timedelta(days=7)
    )
    
    # Remover password_hash de la respuesta
    safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
    
    return LoginResponse(
        user=AdminUser(**safe_user),
        token=access_token,
        refreshToken=refresh_token,
        expiresIn=JWT_EXPIRACION_MINUTOS * 60
    )

@router.get("/admin/auth/me")
async def get_current_admin(token_data: dict = Depends(verify_token)):
    """Obtener información del admin actual"""
    user_data = get_admin_user(token_data["sub"])
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
    return AdminUser(**safe_user)

@router.post("/admin/auth/refresh")
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Renovar token de acceso"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        
        if not payload.get("refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de refresh inválido"
            )
        
        email = payload.get("sub")
        user_data = get_admin_user(email)
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        # Crear nuevo access token
        access_token = create_access_token(
            data={
                "sub": user_data["email"],
                "user_id": user_data["id"],
                "rol": user_data["rol"],
                "empresa": user_data["empresa"]
            }
        )
        
        return {"token": access_token, "expiresIn": JWT_EXPIRACION_MINUTOS * 60}
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresh expirado"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresh inválido"
        )

@router.post("/admin/auth/logout")
async def admin_logout(token_data: dict = Depends(verify_token)):
    """Cerrar sesión (invalidar token)"""
    # En una implementación real, aquí agregarías el token a una blacklist
    return {"message": "Sesión cerrada exitosamente"}

# Inicializar usuarios admin al importar el módulo
init_admin_users()