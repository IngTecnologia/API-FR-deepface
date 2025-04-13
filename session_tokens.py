from datetime import datetime, timedelta
import jwt
import os

# Obtener la clave secreta de una variable de entorno o usar un valor predeterminado
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "clave_segura_para_desarrollo")
TOKEN_EXPIRACION_MINUTOS = 2

def generar_token(cedula: str, tipo_registro: str):
    """
    Genera un JWT token con la información del usuario
    """
    payload = {
        "sub": cedula,  # subject (sujeto del token)
        "tipo_registro": tipo_registro,
        "iat": datetime.utcnow(),  # issued at (cuándo fue emitido)
        "exp": datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRACION_MINUTOS)  # expiration
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def validar_token(token: str, cedula: str):
    """
    Valida un JWT token y verifica que corresponda a la cédula proporcionada
    """

    #Eliminación de comillas extras
    if isinstance(token, str):
        token = token.strip().strip('"')
    if isinstance(cedula, str):
        cedula = cedula.strip().strip('"')
    
    try:
        # Decodificar el token
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        
        # Verificar que la cédula coincida
        if payload["sub"] != cedula:
            return False, "Cédula no coincide con token", None
        
        # Extraer el tipo de registro
        tipo_registro = payload.get("tipo_registro")
        
        return True, "", tipo_registro
        
    except jwt.ExpiredSignatureError as e:
        print(f"Token expirado: {e}")
        return False, "Token de sesión expirado", None
    except jwt.InvalidTokenError as e:
        print(f"Token inválido: {e}")
        return False, "Token de sesión inválido", None
    except Exception as e:
        print(f"Excepción no esperada: {e}")
        return False, f"Error interno: {str(e)}", None