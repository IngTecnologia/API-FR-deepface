"""
Módulo para corregir la orientación de imágenes faciales usando dlib.
Basado en faceorienter pero optimizado para DeepFace.
"""

import cv2
import numpy as np
import os
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class FaceOrientationFixer:
    """
    Clase para detectar y corregir la orientación de imágenes con rostros.
    Utiliza dlib para detección facial y análisis de landmarks.
    """
    
    def __init__(self):
        """Inicializa los detectores de dlib."""
        self.is_available = False
        self.face_detector = None
        self.landmark_detector = None
        
        try:
            import dlib
            
            # Inicializar detector de rostros
            self.face_detector = dlib.get_frontal_face_detector()
            
            # Buscar modelo de landmarks
            model_path = self._find_landmarks_model()
            if model_path:
                self.landmark_detector = dlib.shape_predictor(model_path)
                self.is_available = True
                logger.info("FaceOrientationFixer inicializado correctamente")
            else:
                logger.error("Modelo de landmarks no encontrado")
                
        except ImportError:
            logger.error("dlib no está instalado")
        except Exception as e:
            logger.error(f"Error al inicializar FaceOrientationFixer: {e}")
    
    def _find_landmarks_model(self) -> Optional[str]:
        """Busca el archivo del modelo de landmarks."""
        possible_paths = [
            "shape_predictor_5_face_landmarks.dat",
            "/app/shape_predictor_5_face_landmarks.dat",
            "models/shape_predictor_5_face_landmarks.dat",
            os.path.join(os.path.dirname(__file__), "shape_predictor_5_face_landmarks.dat")
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Modelo de landmarks encontrado: {path}")
                return path
        
        logger.warning("Modelo de landmarks no encontrado en rutas esperadas")
        return None
    
    def _dlib_shape_to_np_array(self, shape) -> np.ndarray:
        """Convierte shape de dlib a numpy array."""
        arr = np.zeros((shape.num_parts, 2), dtype=np.int32)
        for i in range(shape.num_parts):
            arr[i] = (shape.part(i).x, shape.part(i).y)
        return arr
    
    def _rotate_image(self, image: np.ndarray, angle: int) -> np.ndarray:
        """
        Rota una imagen por el ángulo especificado (en sentido horario).
        
        Args:
            image: Imagen a rotar
            angle: Ángulo en grados (90, 180, 270)
            
        Returns:
            Imagen rotada
        """
        if angle == 0:
            return image
        elif angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        else:
            # Rotación genérica para otros ángulos
            (height, width) = image.shape[:2]
            center = (width // 2, height // 2)
            
            matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
            cos = np.abs(matrix[0, 0])
            sin = np.abs(matrix[0, 1])
            
            new_width = int((height * sin) + (width * cos))
            new_height = int((height * cos) + (width * sin))
            
            matrix[0, 2] += (new_width / 2) - center[0]
            matrix[1, 2] += (new_height / 2) - center[1]
            
            return cv2.warpAffine(image, matrix, (new_width, new_height))
    
    def _detect_face_and_landmarks(self, image: np.ndarray) -> Tuple[Optional[np.ndarray], int]:
        """
        Detecta rostros y landmarks, rotando la imagen si es necesario.
        
        Args:
            image: Imagen en formato BGR
            
        Returns:
            Tupla con (landmarks, numero_rotaciones)
        """
        # Convertir a escala de grises
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Intentar detectar rostro sin rotación primero
        faces = self.face_detector(gray, 1)
        n_rotations = 0
        current_gray = gray
        
        # Si no se detecta rostro, probar rotaciones
        if len(faces) == 0:
            for rotation in range(1, 4):  # 90, 180, 270 grados
                rotated_gray = self._rotate_image(gray, rotation * 90)
                faces = self.face_detector(rotated_gray, 1)
                if len(faces) > 0:
                    current_gray = rotated_gray
                    n_rotations = rotation
                    break
        
        # Extraer landmarks si se encontró rostro
        landmarks = None
        if len(faces) > 0:
            try:
                landmarks = self._dlib_shape_to_np_array(
                    self.landmark_detector(current_gray, faces[0])
                )
            except Exception as e:
                logger.warning(f"Error al extraer landmarks: {e}")
        
        return landmarks, n_rotations
    
    def _predict_orientation(self, landmarks: np.ndarray, n_rotations: int) -> str:
        """
        Predice la orientación basándose en los landmarks faciales.
        
        Args:
            landmarks: Array con coordenadas de landmarks (5 puntos)
            n_rotations: Número de rotaciones aplicadas para detectar rostro
            
        Returns:
            Orientación predicha: 'down', 'up', 'left', 'right'
        """
        if landmarks is None or len(landmarks) < 5:
            return 'down'  # Asumir correcta si no hay landmarks válidos
        
        # Extraer puntos del modelo de 5 landmarks:
        # 0: esquina externa ojo izquierdo
        # 1: esquina interna ojo izquierdo  
        # 2: esquina interna ojo derecho
        # 3: esquina externa ojo derecho
        # 4: punta de la nariz
        
        eye_left_outer = landmarks[0]
        eye_left_inner = landmarks[1]
        eye_right_inner = landmarks[2]
        eye_right_outer = landmarks[3]
        nose_tip = landmarks[4]
        
        # Calcular centros de ojos
        eye_left_center = ((eye_left_outer[0] + eye_left_inner[0]) // 2,
                          (eye_left_outer[1] + eye_left_inner[1]) // 2)
        
        eye_right_center = ((eye_right_outer[0] + eye_right_inner[0]) // 2,
                           (eye_right_outer[1] + eye_right_inner[1]) // 2)
        
        # Calcular centro entre ambos ojos
        eyes_center_x = (eye_left_center[0] + eye_right_center[0]) // 2
        eyes_center_y = (eye_left_center[1] + eye_right_center[1]) // 2
        
        # Determinar orientación basándose en posición relativa de la nariz
        # Usamos rangos más amplios para mayor robustez
        
        # Verificar si la nariz está entre los ojos horizontalmente
        min_eye_x = min(eye_left_center[0], eye_right_center[0])
        max_eye_x = max(eye_left_center[0], eye_right_center[0])
        
        # Agregar margen de tolerancia (20% del ancho entre ojos)
        eye_width = max_eye_x - min_eye_x
        tolerance = max(eye_width * 0.2, 10)  # Al menos 10 píxeles de tolerancia
        
        if (min_eye_x - tolerance) <= nose_tip[0] <= (max_eye_x + tolerance):
            # Nariz está aproximadamente entre los ojos horizontalmente
            if nose_tip[1] >= eyes_center_y:
                orientation = 0  # down - imagen correcta
            else:
                orientation = 2  # up - imagen invertida
        else:
            # Nariz está a un lado de los ojos
            if nose_tip[0] >= eyes_center_x:
                orientation = 3  # left - rotado hacia la izquierda
            else:
                orientation = 1  # right - rotado hacia la derecha
        
        # Ajustar por las rotaciones aplicadas durante detección
        orientations = ['down', 'right', 'up', 'left']
        final_orientation = orientations[(n_rotations + orientation) % 4]
        
        return final_orientation
    
    def _calculate_rotation_needed(self, predicted_orientation: str) -> int:
        """
        Calcula los grados de rotación necesarios para corregir orientación.
        
        Args:
            predicted_orientation: Orientación detectada
            
        Returns:
            Grados de rotación necesarios (0, 90, 180, 270)
        """
        rotation_map = {
            'down': 0,    # Ya está correcto
            'right': 270, # Rotar 270° (equivale a -90°)
            'up': 180,    # Rotar 180°
            'left': 90    # Rotar 90°
        }
        return rotation_map.get(predicted_orientation, 0)
    
    def fix_image_orientation(self, image: np.ndarray) -> Tuple[np.ndarray, bool]:
        """
        Corrige la orientación de una imagen con rostro.
        
        Args:
            image: Imagen en formato BGR (OpenCV)
            
        Returns:
            Tupla con (imagen_corregida, fue_corregida)
        """
        if not self.is_available:
            logger.warning("FaceOrientationFixer no disponible, devolviendo imagen original")
            return image, False
        
        try:
            # Verificar que la imagen sea válida
            if image is None or image.size == 0:
                logger.warning("Imagen inválida para corrección de orientación")
                return image, False
            
            # Detectar landmarks y orientación
            landmarks, n_rotations = self._detect_face_and_landmarks(image)
            
            if landmarks is None:
                logger.warning("No se pudo detectar rostro para corrección de orientación")
                return image, False
            
            # Predecir orientación
            predicted_orientation = self._predict_orientation(landmarks, n_rotations)
            logger.debug(f"Orientación detectada: {predicted_orientation}")
            
            # Calcular rotación necesaria
            rotation_needed = self._calculate_rotation_needed(predicted_orientation)
            
            if rotation_needed == 0:
                logger.debug("Imagen ya está correctamente orientada")
                return image, False
            
            # Aplicar corrección
            corrected_image = self._rotate_image(image, rotation_needed)
            logger.info(f"Imagen corregida: rotación de {rotation_needed}° (orientación detectada: {predicted_orientation})")
            
            return corrected_image, True
            
        except Exception as e:
            logger.error(f"Error al corregir orientación: {e}")
            return image, False

# Instancia global para reutilizar
_face_orientation_fixer = None

def get_face_orientation_fixer() -> FaceOrientationFixer:
    """Obtiene instancia singleton del corrector de orientación."""
    global _face_orientation_fixer
    if _face_orientation_fixer is None:
        _face_orientation_fixer = FaceOrientationFixer()
    return _face_orientation_fixer

def fix_face_orientation_from_file(image_path: str, output_path: Optional[str] = None) -> Tuple[str, bool]:
    """
    Función de conveniencia para corregir orientación de imagen desde archivo.
    
    Args:
        image_path: Ruta de imagen de entrada
        output_path: Ruta de salida (opcional, sobrescribe si None)
        
    Returns:
        Tupla con (ruta_imagen_final, fue_corregida)
    """
    try:
        # Leer imagen
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"No se pudo leer la imagen: {image_path}")
        
        # Corregir orientación
        fixer = get_face_orientation_fixer()
        corrected_image, was_corrected = fixer.fix_image_orientation(image)
        
        # Determinar ruta de salida
        final_path = output_path or image_path
        
        # Guardar imagen (corregida o original)
        cv2.imwrite(final_path, corrected_image)
        
        return final_path, was_corrected
        
    except Exception as e:
        logger.error(f"Error al procesar archivo {image_path}: {e}")
        return image_path, False