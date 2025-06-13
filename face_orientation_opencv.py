"""
Corrector de orientación usando solo OpenCV.
Optimizado para velocidad y simplicidad.
"""

import cv2
import numpy as np
from typing import Tuple
import logging
import os

logger = logging.getLogger(__name__)

class OpenCVOrientationFixer:
    """Corrector de orientación usando detectores de OpenCV."""
    
    def __init__(self):
        """Inicializa el detector de rostros de OpenCV."""
        try:
            # Usar detector de cascada de OpenCV
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if not os.path.exists(cascade_path):
                raise FileNotFoundError(f"Archivo de cascada no encontrado: {cascade_path}")
            
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            
            # Verificar que se cargó correctamente
            if self.face_cascade.empty():
                raise ValueError("El clasificador de cascada está vacío")
            
            self.is_available = True
            logger.info("OpenCVOrientationFixer inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar OpenCVOrientationFixer: {e}")
            self.is_available = False
    
    def _rotate_image_fast(self, image: np.ndarray, angle: int) -> np.ndarray:
        """Rota imagen usando funciones optimizadas de OpenCV."""
        if angle == 0:
            return image
        elif angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            # Para ángulos no estándar (no debería pasar en este caso)
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            return cv2.warpAffine(image, matrix, (w, h))
    
    def _detect_faces_in_orientation(self, gray_image: np.ndarray) -> Tuple[int, float]:
        """
        Detecta rostros y calcula una puntuación de confianza.
        
        Returns:
            (número_rostros, puntuación_confianza)
        """
        try:
            faces = self.face_cascade.detectMultiScale(
                gray_image,
                scaleFactor=1.1,
                minNeighbors=3,  # Reducido para ser menos estricto
                minSize=(20, 20),  # Tamaño mínimo más pequeño
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            if len(faces) == 0:
                return 0, 0.0
            
            # Calcular puntuación basada en el rostro más grande
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            area = largest_face[2] * largest_face[3]
            
            # Normalizar la puntuación (área típica de rostro: 1000-10000 píxeles)
            confidence = min(area / 1000.0, 10.0)
            
            return len(faces), confidence
            
        except Exception as e:
            logger.error(f"Error en detección de rostros: {e}")
            return 0, 0.0
    
    def _find_best_orientation(self, image: np.ndarray) -> Tuple[int, float]:
        """
        Encuentra la mejor orientación probando rotaciones.
        
        Returns:
            (mejor_rotación, mejor_confianza)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        best_rotation = 0
        best_confidence = 0.0
        best_face_count = 0
        
        # Probar las 4 orientaciones básicas
        rotations_to_test = [0, 90, 180, 270]
        
        for rotation in rotations_to_test:
            # Rotar imagen
            if rotation == 0:
                test_gray = gray
            else:
                test_gray = self._rotate_image_fast(gray, rotation)
            
            # Detectar rostros
            face_count, confidence = self._detect_faces_in_orientation(test_gray)
            
            # Determinar si esta orientación es mejor
            is_better = False
            if face_count > best_face_count:
                is_better = True
            elif face_count == best_face_count and confidence > best_confidence:
                is_better = True
            
            if is_better:
                best_face_count = face_count
                best_confidence = confidence
                best_rotation = rotation
        
        return best_rotation, best_confidence
    
    def fix_image_orientation(self, image: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Corrige la orientación de una imagen con rostro.
        
        Args:
            image: Imagen en formato BGR (OpenCV)
            
        Returns:
            Tupla con (imagen_corregida, fue_corregida)
        """
        if not self.is_available:
            logger.warning("OpenCVOrientationFixer no disponible, devolviendo imagen original")
            return image, False
        
        try:
            # Verificar que la imagen sea válida
            if image is None or image.size == 0:
                logger.warning("Imagen inválida para corrección de orientación")
                return image, False
            
            # Encontrar la mejor orientación
            best_rotation, confidence = self._find_best_orientation(image)
            
            # Si no se detectó rostro en ninguna orientación
            if confidence == 0:
                logger.warning("No se pudo detectar rostro en ninguna orientación")
                return image, False
            
            # Si ya está en la orientación correcta (0°)
            if best_rotation == 0:
                logger.debug("Imagen ya está correctamente orientada")
                return image, False
            
            # Calcular rotación necesaria para corregir
            # Si el rostro se ve mejor rotado X°, necesitamos rotar -X° para corregir
            if best_rotation == 90:
                correction_angle = 270  # Rotar 270° para corregir
            elif best_rotation == 180:
                correction_angle = 180  # Rotar 180° para corregir
            #elif best_rotation == 270:
                #correction_angle = 90   # Rotar 90° para corregir
            else:
                correction_angle = 0
            
            # Aplicar corrección
            corrected_image = self._rotate_image_fast(image, correction_angle)
            
            logger.info(f"Imagen corregida: rotación de {correction_angle}° (rostro detectado en {best_rotation}°)")
            return corrected_image, True
            
        except Exception as e:
            logger.error(f"Error al corregir orientación: {e}")
            return image, False

# Instancia global para reutilizar (patrón singleton)
_opencv_orientation_fixer = None

def get_opencv_orientation_fixer() -> OpenCVOrientationFixer:
    """Obtiene la instancia singleton del corrector de orientación."""
    global _opencv_orientation_fixer
    if _opencv_orientation_fixer is None:
        _opencv_orientation_fixer = OpenCVOrientationFixer()
    return _opencv_orientation_fixer

def fix_image_orientation(image_path: str) -> Tuple[bool, str]:
    """
    Función de conveniencia para corregir orientación desde archivo.
    
    Args:
        image_path: Ruta de la imagen a corregir
        
    Returns:
        Tupla con (fue_corregida, mensaje_log)
    """
    try:
        # Leer imagen
        image = cv2.imread(image_path)
        if image is None:
            return False, f"No se pudo leer la imagen: {image_path}"
        
        # Corregir orientación
        fixer = get_opencv_orientation_fixer()
        corrected_image, was_corrected = fixer.fix_image_orientation(image)
        
        # Sobrescribir archivo si fue corregido
        if was_corrected:
            cv2.imwrite(image_path, corrected_image)
            return True, "Imagen corregida y guardada"
        else:
            return False, "Imagen no requería corrección"
            
    except Exception as e:
        return False, f"Error al procesar imagen: {str(e)}"