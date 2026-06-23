import os
import hashlib
import zipfile
from fontTools.ttLib import TTFont

def obtener_hash(ruta_archivo):
    hasher = hashlib.md5()
    with open(ruta_archivo, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def validar_fuente(ruta):
    # Nota: PFB/PFM son formatos antiguos que fontTools no siempre valida 
    # estructuralmente igual que TTF/OTF. Se marcarán como "Revisar (Legacy)"
    if ruta.lower().endswith(('.pfb', '.pfm')):
        return True, "Legacy (PFB/PFM)"
    try:
        font = TTFont(ruta)
        font.close()
        return True, "OK"
    except Exception:
        return False, "Corrupta"

def auditar_carpeta(ruta_base):
    archivos_vistos = {}
    resultado = []
    
    for raiz, _, archivos in os.walk(ruta_base):
        for nombre in archivos:
            ruta_completa = os.path.join(raiz, nombre)
            ext = nombre.lower()

            # Caso 1: Archivos comprimidos ZIP
            if ext.endswith('.zip'):
                with zipfile.ZipFile(ruta_completa, 'r') as z:
                    for contenido in z.namelist():
                        if contenido.lower().endswith(('.ttf', '.otf', '.pfb', '.pfm')):
                            resultado.append(f"{nombre} -> Contenido: {contenido} | Comprimido")
                continue

            # Caso 2: Fuentes directas
            if ext.endswith(('.ttf', '.otf', '.pfb', '.pfm')):
                es_valida, estado = validar_fuente(ruta_completa)
                
                if es_valida and not ext.endswith(('.pfb', '.pfm')):
                    h = obtener_hash(ruta_completa)
                    if h in archivos_vistos:
                        estado = f"Duplicado de: {archivos_vistos[h]}"
                    else:
                        archivos_vistos[h] = nombre
                
                resultado.append(f"{nombre} | {estado}")
                print(f"Procesado: {nombre} -> {estado}")
    
    with open("reporte_fuentes_completo.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(resultado))
    print("\nAuditoría finalizada. Reporte guardado: reporte_fuentes_completo.txt")

# CAMBIA LA RUTA ABAJO
ruta_de_tus_fuentes = r"E:\Web\Fuentes-Fonts"
auditar_carpeta(ruta_de_tus_fuentes)