# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
# Local development
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Docker development
docker-compose up --build

# Production (Docker)
docker-compose up -d
```

### Dependencies
```bash
# Install dependencies
pip install -r requirements.txt

# Update dependencies
pip freeze > requirements.txt
```

## Application Architecture

### FastAPI Modular Structure
The application follows a modular FastAPI architecture with separate routers for different functionalities:

- **main.py**: Entry point, combines all routers and configures CORS
- **config.py**: Centralized configuration including JWT settings, API keys, file paths, and DeepFace parameters
- **Router modules**:
  - `verify_web.py`: Two-step web/mobile verification (location → face)
  - `verify_terminal.py`: Terminal-based verification with API key authentication
  - `user_registration.py`: User registration with facial image storage
  - `attendance_records.py`: Attendance record management and retrieval
  - `terminal_sync.py`: Terminal synchronization functionality

### Core Components

#### Authentication & Security
- **JWT tokens**: Generated in `session_tokens.py` for web verification workflow
- **API key authentication**: Used for terminal access, configured in `config.py`
- **Two-factor verification**: Combines geolocation + facial recognition

#### Facial Recognition Pipeline
- **DeepFace integration**: Uses SFace model with OpenCV backend
- **Anti-spoofing**: Configurable detection to prevent photo/video attacks
- **Image processing**: Automatic rotation and orientation correction in `face_orientation_*` modules
- **Storage**: Base images in `imagenes_base/`, temporary uploads in `tmp_uploads/`

#### Data Storage
- **JSON-based**: All data stored in local JSON files in `data/` directory
- **Files**:
  - `usuarios.json`: User profiles and registration data
  - `registros.json`: Attendance records
  - `ubicaciones.json`: Location data for geofencing
  - `solicitudes_registro.json`: Terminal registration requests

#### Geolocation System
- **Location verification**: `location.py` handles distance calculations and geofencing
- **Multi-location support**: Users can have multiple allowed locations
- **Configurable radius**: Per-location radius settings for attendance validation

### Key Workflows

#### Web/Mobile Verification (Two-step)
1. **POST /verify-web/init**: Location validation → JWT token generation
2. **POST /verify-web/face**: Face verification using token

#### Terminal Verification (Single-step)
1. **POST /verify-terminal**: Combined location + face verification with API key

#### User Registration
1. **POST /register-user**: Creates user profile with facial reference image

### Docker Configuration
- **Multi-service**: API + Nginx reverse proxy
- **Volume mounts**: Persistent storage for images and data
- **Environment variables**: Configurable file paths and settings
- **Port mapping**: 8000 (API), 80/443 (Nginx)

### Data Models
- **Record**: Attendance record with verification status, location data, and metadata
- **User**: Profile with company, location preferences, and facial reference
- **Location**: Geofencing data with radius and coordinates

## Important Configuration
- **Face model**: SFace (configured in config.py)
- **Token expiration**: 2-7 minutes for session tokens
- **File paths**: Configurable through environment variables
- **Multi-company support**: Built-in enterprise separation

## Development Notes
- All image processing includes automatic rotation/orientation correction
- JSON files are auto-created if missing
- Temporary files are cleaned up after processing
- CORS enabled for all origins (restrict in production)
- UTC timestamps used throughout