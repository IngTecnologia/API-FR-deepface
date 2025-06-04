from deepface import DeepFace
from config import ANTI_SPOOFING


result = DeepFace.extract_faces(img_path="C:/Users/Jesus.Cortes/OneDrive - INEMEC/Documentos/API-FR-deepface/imagenes_base/1003237039.jpg", anti_spoofing=ANTI_SPOOFING)
print(result)

