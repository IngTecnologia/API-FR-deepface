# 🧩 API de Reconocimiento Facial para Control de Asistencia

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-green?logo=fastapi)
![DeepFace](https://img.shields.io/badge/DeepFace-Enabled-lightgrey?logo=deep-learning)
![Docker](https://img.shields.io/badge/Docker-Supported-blue?logo=docker)
![Licencia](https://img.shields.io/badge/Licencia-INEMEC-red)

Esta API proporciona un sistema de verificación biométrica facial para control de asistencia, desarrollado con **FastAPI** y **DeepFace**.

---

## 🚀 Características principales

- 🧠 **Verificación biométrica facial**: Utiliza redes neuronales convolucionales (Deep Learning) para un reconocimiento facial preciso.
- 🔒 **Doble factor de autenticación**: Combina verificación facial con geolocalización.
- 🌐 **Múltiples métodos de acceso**: Compatible con terminales físicas y aplicaciones web/móviles.
- 🗄️ **Control total de datos**: Almacenamiento local de toda la información, sin dependencias de servicios externos.
- 🕵️ **Detección de suplantación** *(anti-spoofing)*: Evita intentos de fraude mediante fotografías o vídeos.
- 🏢 **Soporte multi-empresa**: Diseñado para manejar datos de múltiples organizaciones.

---

## 🧩 Requisitos

- 🐍 Python 3.10+
- 🧠 DeepFace
- ⚡ FastAPI
- 🔥 Uvicorn
- 👁️ OpenCV
- 🛡️ PyJWT
- 📦 Otras dependencias en `requirements.txt`

---

## ⚙️ Instalación

### 🐳 Usando Docker (recomendado)

```bash
# Clonar el repositorio
git clone https://github.com/IngTecnologia/API-FR-deepface.git
cd API-FR-deepface

# Construir y ejecutar con Docker Compose
docker-compose up --build
```

### 🖥️ Instalación manual

```bash
# Clonar el repositorio
git clone https://github.com/IngTecnologia/API-FR-deepface.git
cd API-FR-deepface

# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar la API
uvicorn main:app --host 0.0.0.0 --port 8000
```

---

## 🗂️ Estructura del proyecto

```bash
api/
├── imagenes_base/          # Directorio para almacenar imágenes faciales de referencia
├── tmp_uploads/            # Directorio temporal para subida de imágenes
├── attendance_records.py   # Gestión de registros de asistencia
├── config.py               # Configuración centralizada
├── docker-compose.yml      # Configuración para Docker Compose
├── Dockerfile              # Definición de la imagen Docker
├── main.py                 # Punto de entrada de la aplicación
├── session_tokens.py       # Implementación de tokens JWT para sesiones
├── terminal_sync.py        # Sincronización con terminales físicas
├── user_registration.py    # Registro de usuarios en el sistema
├── verify_terminal.py      # Verificación para terminales físicas
├── verify_web.py           # Verificación para aplicaciones web/móviles
└── requirements.txt        # Dependencias del proyecto
```

---

## 🛠️ Endpoints principales

### 📲 Verificación web/móvil

- **POST /verify-web/init:** Primer paso, verifica la ubicación geográfica del usuario y genera un token de sesión.

```json
{
  "cedula": "1234567890",
  "lat": 4.6867602,
  "lng": -74.0529746,
  "tipo_registro": "entrada"
}
```

- **POST /verify-web/face:** Segundo paso, realiza la verificación facial utilizando el token generado.

```json
{
  "cedula": "1234567890",
  "session_token": "eyJhbGciOiJIUzI1NiIsI...",
  "image": "[archivo de imagen]"
}
```

### 🏷️ Verificación en terminal física

- **POST /verify-terminal:** Verificación para terminales físicas (requiere API key).

```json
{
  "cedula": "1234567890",
  "terminal_id": "TERMINAL_001",
  "tipo_registro": "entrada",
  "image": "[archivo de imagen]",
  "x-api-key": "mi_api_key_segura_001"
}
```

### 🧑‍💻 Registro de usuarios

- **POST /register-user:** Registra un nuevo usuario en el sistema.

```json
{
  "cedula": "1234567890",
  "nombre": "Juan Pérez",
  "empresa": "INEMEC",
  "terminal_id": "TERMINAL_001",
  "imagen": "[archivo de imagen]",
  "lat": 4.6867602,
  "lng": -74.0529746,
  "radio_metros": 200
}
```

---

## 📝 Registros de asistencia

- **GET /records/{cedula}:** Obtiene registros de asistencia por cédula.
- **GET /records/date/{fecha}:** Obtiene registros de asistencia por fecha.
- **GET /records/company/{empresa}:** Obtiene registros de asistencia por empresa.

---

## ⚙️ Configuración

Las configuraciones principales se encuentran en `config.py`:

- `JWT_SECRET_KEY`: 🔐 Clave para firmar los tokens JWT
- `API_KEYS`: 🗝️ Claves de API para terminales físicas
- `FACE_MODEL`: 🧠 Modelo de reconocimiento facial a utilizar
- `ANTI_SPOOFING`: 🕵️‍♂️ Activar/desactivar la detección de suplantación

---

## 🔒 Seguridad

- ✅ Los tokens de sesión utilizan JWT (JSON Web Tokens).
- 🧹 Las imágenes temporales se eliminan automáticamente después de su procesamiento.
- 🔑 Las terminales físicas requieren autenticación por API key.
- 🧼 Se implementa limpieza de inputs para prevenir inyecciones.

---

## 🧩 Contribuciones

¡Las contribuciones son bienvenidas!  
Por favor abre un *issue* o envía un *pull request* para mejorar este proyecto.

---

## 📋 To-Do

- [x] Dockerización del proyecto
- [x] Soporte para múltiples empresas
- [ ] Endpoint de administración para gestión de usuarios
- [ ] Panel de administración web
- [ ] Integración con base de datos externa (PostgreSQL/MySQL)

---

## 📄 Licencia

Este proyecto es propiedad de **INEMEC**.  
**Todos los derechos reservados.**

---

## 👤 Autor

Desarrollado por **Ing. Jesús Cotes**

[![GitHub](https://img.shields.io/badge/GitHub-@IngTecnologia-black?logo=github)](https://github.com/IngTecnologia)