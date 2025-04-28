def calcular_distancia_m(lat1, lng1, lat2, lng2):
    """Calcula la distancia en metros entre dos coordenadas."""
    import math
    R = 6371000  # Radio de la Tierra en metros
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def verificar_ubicacion(lat, lng, ubicaciones_usuario):
    """Verifica si el usuario está dentro de alguna de sus ubicaciones.
    
    Args:
        lat: Latitud actual del usuario
        lng: Longitud actual del usuario
        ubicaciones_usuario: Lista de ubicaciones del usuario
        
    Returns:
        (bool, float, str): Tupla con (está_en_ubicación, distancia_mínima, nombre_ubicación)
    """
    if not ubicaciones_usuario:
        return False, 0, ""
    
    # Si es formato antiguo, convertir a lista
    if not isinstance(ubicaciones_usuario, list):
        if "ubicaciones" in ubicaciones_usuario:
            ubicaciones_usuario = ubicaciones_usuario["ubicaciones"]
        else:
            ubicaciones_usuario = [{
                "lat": ubicaciones_usuario.get("lat", 0),
                "lng": ubicaciones_usuario.get("lng", 0),
                "radio_metros": ubicaciones_usuario.get("radio_metros", 200),
                "nombre": "Principal"
            }]
    
    # Verificar cada ubicación
    distancia_minima = float('inf')
    nombre_ubicacion = ""
    en_ubicacion = False
    
    for ubicacion in ubicaciones_usuario:
        distancia = calcular_distancia_m(lat, lng, ubicacion["lat"], ubicacion["lng"])
        
        if distancia < distancia_minima:
            distancia_minima = distancia
            nombre_ubicacion = ubicacion["nombre"]
            
            if distancia <= ubicacion["radio_metros"]:
                en_ubicacion = True
    
    return en_ubicacion, distancia_minima, nombre_ubicacion