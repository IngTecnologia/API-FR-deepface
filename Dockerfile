FROM python:3.10.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para OpenCV y DeepFace
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi==0.95.1 \
    uvicorn[standard]==0.22.0 \
    deepface==0.0.79 \
    opencv-python==4.7.0.72 \
    python-multipart==0.0.6 \
    tensorflow==2.12.0 \
    pyjwt==2.7.0

# Crear directorios necesarios
RUN mkdir -p imagenes_base tmp_uploads

# Copiar el código de la aplicación
COPY . /app/

# Exponer puerto
EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]