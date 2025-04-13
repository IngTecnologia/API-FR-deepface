from deepface import DeepFace


result = DeepFace.extract_faces(img_path="C:/Users/jesus/OneDrive/Documents/INEMEC/registros/pruebas/api_own/api/src/tmp_uploads/123456789_1743018124.152798.jpg", anti_spoofing= True)
print(result)

