import json
import os
from config import UBICACIONES_FILE, RECORDS_FILE, USERS_FILE

def migrar_ubicaciones():
    """Migra el formato de ubicaciones al nuevo esquema."""
    if not os.path.exists(UBICACIONES_FILE):
        print(f"El archivo {UBICACIONES_FILE} no existe.")
        return False
    
    try:
        with open(UBICACIONES_FILE, "r") as f:
            ubicaciones = json.load(f)
        
        # Crear respaldo
        with open(f"{UBICACIONES_FILE}.bak", "w") as f:
            json.dump(ubicaciones, f, indent=2)
        
        # Verificar si ya está en el nuevo formato
        if ubicaciones and "ubicaciones" in ubicaciones[0]:
            print("El archivo ya parece estar en el nuevo formato.")
            return False
        
        # Convertir al nuevo formato
        nuevas_ubicaciones = []
        for ubicacion in ubicaciones:
            nuevas_ubicaciones.append({
                "cedula": ubicacion["cedula"],
                "nombre_usuario": ubicacion.get("nombre", "Usuario"),
                "ubicaciones": [{
                    "lat": ubicacion.get("lat", 0),
                    "lng": ubicacion.get("lng", 0),
                    "radio_metros": ubicacion.get("radio_metros", 200),
                    "nombre": "Principal"
                }]
            })
        
        # Guardar
        with open(UBICACIONES_FILE, "w", encoding="utf-8") as f:
            json.dump(nuevas_ubicaciones, f, indent=2, ensure_ascii=False)
        
        print(f"Migración exitosa. Se actualizaron {len(nuevas_ubicaciones)} registros.")
        return True
    
    except Exception as e:
        print(f"Error durante la migración: {e}")
        return False

def agregar_perfil_ubicacion():
    """Agrega el campo perfil_ubicacion a los usuarios existentes."""
    if not os.path.exists(USERS_FILE):
        print(f"El archivo {USERS_FILE} no existe.")
        return False
    
    try:
        with open(USERS_FILE, "r") as f:
            usuarios = json.load(f)
        
        # Crear respaldo
        with open(f"{USERS_FILE}.bak", "w") as f:
            json.dump(usuarios, f, indent=2)
        
        # Agregar campo si no existe
        actualizados = 0
        for usuario in usuarios:
            if "perfil_ubicacion" not in usuario:
                usuario["perfil_ubicacion"] = "fijo"  # Valor por defecto
                actualizados += 1
        
        # Guardar
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(usuarios, f, indent=2, ensure_ascii=False)
        
        print(f"Actualización exitosa. Se actualizaron {actualizados} usuarios.")
        return True
    
    except Exception as e:
        print(f"Error durante la actualización: {e}")
        return False

def agregar_campos_registros():
    """Agrega los nuevos campos a los registros existentes."""
    if not os.path.exists(RECORDS_FILE):
        print(f"El archivo {RECORDS_FILE} no existe.")
        return False
    
    try:
        with open(RECORDS_FILE, "r") as f:
            registros = json.load(f)
        
        # Crear respaldo
        with open(f"{RECORDS_FILE}.bak", "w") as f:
            json.dump(registros, f, indent=2)
        
        # Agregar campos si no existen
        actualizados = 0
        for registro in registros:
            modificado = False
            
            if "fuera_de_ubicacion" not in registro:
                registro["fuera_de_ubicacion"] = False
                modificado = True
            
            if "comentario" not in registro:
                registro["comentario"] = ""
                modificado = True
                
            if "ubicacion_nombre" not in registro:
                registro["ubicacion_nombre"] = "Principal"
                modificado = True
            
            if modificado:
                actualizados += 1
        
        # Guardar
        with open(RECORDS_FILE, "w", encoding="utf-8") as f:
            json.dump(registros, f, indent=2, ensure_ascii=False)
        
        print(f"Actualización exitosa. Se actualizaron {actualizados} registros.")
        return True
    
    except Exception as e:
        print(f"Error durante la actualización: {e}")
        return False

if __name__ == "__main__":
    print("Iniciando migración de datos...")
    print("1. Migrando formato de ubicaciones...")
    migrar_ubicaciones()
    print("2. Agregando campo perfil_ubicacion a usuarios...")
    agregar_perfil_ubicacion()
    print("3. Actualizando campos en registros existentes...")
    agregar_campos_registros()
    print("Migración completada.")