import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import hashlib
import zipfile

class GestorFuentesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Inteligente de Fuentes")
        self.root.geometry("900x650")
        
        self.archivo_indice = {} # Almacena {hash: [ruta1, ruta2]}

        # --- Contenedor Superior (Ruta) ---
        frame_top = tk.Frame(root)
        frame_top.pack(pady=10, padx=10, fill=tk.X)
        
        tk.Label(frame_top, text="Carpeta de Fuentes:").pack(side=tk.LEFT)
        
        self.entry_ruta = tk.Entry(frame_top)
        self.entry_ruta.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.btn_select = tk.Button(frame_top, text="Seleccionar", command=self.seleccionar_carpeta)
        self.btn_select.pack(side=tk.LEFT)

        # --- Listado (Tabla) ---
        self.tree = ttk.Treeview(root, columns=("Ruta", "Estado", "Tipo"), show='headings')
        self.tree.heading("Ruta", text="Nombre del Archivo")
        self.tree.heading("Estado", text="Estado")
        self.tree.heading("Tipo", text="Formato")
        self.tree.column("Ruta", width=400)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Botones Inferiores ---
        frame_bottom = tk.Frame(root)
        frame_bottom.pack(pady=10)
        
        self.btn_auditar = tk.Button(frame_bottom, text="2. Recorrer y Analizar Fuentes", command=self.iniciar_auditoria, bg="#e1e1e1")
        self.btn_auditar.pack(side=tk.LEFT, padx=5)
        
        self.btn_reporte = tk.Button(frame_bottom, text="Generar Reporte TXT", command=self.generar_reporte)
        self.btn_reporte.pack(side=tk.LEFT, padx=5)

    def obtener_hash(self, ruta_archivo):
        hasher = hashlib.md5()
        try:
            with open(ruta_archivo, 'rb') as f:
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            return hasher.hexdigest()
        except:
            return "ERROR_HASH"

    def seleccionar_carpeta(self):
        ruta = filedialog.askdirectory()
        if ruta:
            self.entry_ruta.delete(0, tk.END)
            self.entry_ruta.insert(0, ruta)

    def iniciar_auditoria(self):
        ruta = self.entry_ruta.get()
        if not os.path.exists(ruta):
            messagebox.showerror("Error", "La ruta no existe.")
            return
        
        # Limpiar tabla
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        self.archivo_indice = {}
        messagebox.showinfo("Procesando", "Iniciando análisis profundo...")
        
        # Ejecutar en hilo separado para no congelar la UI
        thread = threading.Thread(target=self.ejecutar_analisis_fondo, args=(ruta,), daemon=True)
        thread.start()

    def ejecutar_analisis_fondo(self, ruta):
        for root, dirs, files in os.walk(ruta):
            for file in files:
                path = os.path.join(root, file)
                
                # Procesar archivos sueltos
                if file.lower().endswith(('.ttf', '.otf', '.pfb', '.pfm')):
                    h = self.obtener_hash(path)
                    self.registrar_en_indice(h, path, file, "Fuente")
                
                # Procesar ZIPS
                elif file.lower().endswith('.zip'):
                    try:
                        with zipfile.ZipFile(path, 'r') as z:
                            for name in z.namelist():
                                if name.lower().endswith(('.ttf', '.otf')):
                                    # Marcamos relación
                                    self.registrar_en_indice(f"ZIP_{file}", path, f"{file} -> {name}", "Comprimido")
                    except:
                        pass
        
        self.root.after(0, lambda: messagebox.showinfo("Completado", "Análisis finalizado. Resultados listados."))

    def registrar_en_indice(self, h, path, nombre_display, tipo):
        if h not in self.archivo_indice:
            self.archivo_indice[h] = []
        self.archivo_indice[h].append(path)
        
        estado = "Duplicado" if len(self.archivo_indice[h]) > 1 else "OK"
        
        # Actualizar la UI desde el hilo principal
        self.root.after(0, lambda: self.tree.insert("", "end", values=(nombre_display, estado, tipo)))

    def generar_reporte(self):
        if not self.archivo_indice:
            messagebox.showwarning("Aviso", "Primero realiza un análisis.")
            return
            
        with open("reporte_fuentes_completo.txt", "w", encoding="utf-8") as f:
            for h, paths in self.archivo_indice.items():
                estado = "DUPLICADO" if len(paths) > 1 else "OK"
                f.write(f"Estado: {estado} | Archivos: {paths}\n")
        
        messagebox.showinfo("Éxito", "Reporte generado: reporte_fuentes_completo.txt")

if __name__ == "__main__":
    root = tk.Tk()
    app = GestorFuentesApp(root)
    root.mainloop()