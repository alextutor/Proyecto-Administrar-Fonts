import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import os
import hashlib
import zipfile
import shutil
from PIL import Image, ImageDraw, ImageFont, ImageTk

class GestorFuentesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Inteligente de Fuentes - Auditoría Profesional")
        self.root.geometry("1100x750")
        
        self.archivo_indice = {} # Almacena {hash: [lista_de_rutas]}
        self.is_running = False
        self.total_encontradas = 0
        self.total_duplicadas = 0

        # --- Top: Selección ---
        frame_top = tk.LabelFrame(root, text="Configuración")
        frame_top.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(frame_top, text="Carpeta de Fuentes:").pack(side=tk.LEFT, padx=5)
        self.entry_ruta = tk.Entry(frame_top)
        self.entry_ruta.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(frame_top, text="Seleccionar", command=self.seleccionar_carpeta).pack(side=tk.LEFT, padx=5)

        # --- Centro: Tabla y Preview ---
        frame_mid = tk.Frame(root)
        frame_mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Tabla con Scrollbar
        self.tree = ttk.Treeview(frame_mid, columns=("Ruta", "Estado", "Tipo"), show='headings')
        self.tree.heading("Ruta", text="Nombre del Archivo")
        self.tree.heading("Estado", text="Estado")
        self.tree.heading("Tipo", text="Formato")
        self.tree.column("Ruta", width=450)
        
        scrollbar = ttk.Scrollbar(frame_mid, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        
        self.tree.bind("<<TreeviewSelect>>", self.previsualizar_fuente)

        # Panel de Preview
        self.lbl_preview = tk.Label(frame_mid, text="Seleccione una fuente\npara previsualizar", bg="#f0f0f0", width=30, height=15, relief="sunken")
        self.lbl_preview.pack(side=tk.RIGHT, padx=10, fill=tk.Y)

        # --- Bottom: Controles y Progreso ---
        frame_bottom = tk.Frame(root)
        frame_bottom.pack(fill=tk.X, padx=10, pady=10)

        # Botones
        self.btn_auditar = tk.Button(frame_bottom, text="2. Recorrer y Analizar Fuentes", command=self.iniciar_auditoria, bg="#c8e6c9")
        self.btn_auditar.pack(side=tk.LEFT, padx=5)
        
        self.btn_reporte = tk.Button(frame_bottom, text="Generar Reporte TXT", command=self.generar_reporte, bg="#bbdefb")
        self.btn_reporte.pack(side=tk.LEFT, padx=5)
        
        self.btn_borrar = tk.Button(frame_bottom, text="Borrar Seleccionado", command=self.borrar_seleccionado, bg="#ffcc80")
        self.btn_borrar.pack(side=tk.LEFT, padx=5)
        
        self.btn_cancelar = tk.Button(frame_bottom, text="Cancelar", command=self.cancelar_proceso, bg="#ffcdd2", state=tk.DISABLED)
        self.btn_cancelar.pack(side=tk.LEFT, padx=5)

        # Progreso
        self.progress = ttk.Progressbar(frame_bottom, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Barra de estado
        self.status_var = tk.StringVar(value="Listo. Fuentes: 0 | Duplicados: 0")
        self.lbl_status = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

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
            return "ERROR"

    def seleccionar_carpeta(self):
        ruta = filedialog.askdirectory()
        if ruta:
            self.entry_ruta.delete(0, tk.END)
            self.entry_ruta.insert(0, ruta)

    def cancelar_proceso(self):
        self.is_running = False
        self.status_var.set("Cancelando...")

    def borrar_seleccionado(self):
        selected = self.tree.selection()
        if not selected: 
            messagebox.showwarning("Aviso", "Selecciona una fila de la tabla primero.")
            return
        
        # Implementación simple: borraría la ruta asociada
        # En una app real, aquí buscarías la ruta en self.archivo_indice
        messagebox.showinfo("Acción", "Función de borrado activada. (Requiere ruta completa en la tabla)")

    def previsualizar_fuente(self, event):
        self.lbl_preview.config(text="Previsualización\n(Requiere Pillow instalado)")

    def iniciar_auditoria(self):
        ruta = self.entry_ruta.get()
        if not os.path.exists(ruta):
            messagebox.showerror("Error", "La ruta no existe.")
            return
        
        self.is_running = True
        self.archivo_indice = {}
        self.total_encontradas = 0
        self.total_duplicadas = 0
        
        for i in self.tree.get_children(): self.tree.delete(i)
        
        self.btn_auditar.config(state=tk.DISABLED)
        self.btn_cancelar.config(state=tk.NORMAL)
        
        threading.Thread(target=self.ejecutar_analisis, args=(ruta,), daemon=True).start()

    def ejecutar_analisis(self, ruta):
        lista_archivos = []
        for root, _, files in os.walk(ruta):
            for f in files:
                if f.lower().endswith(('.ttf', '.otf', '.pfb', '.pfm', '.zip')):
                    lista_archivos.append(os.path.join(root, f))
        
        total = len(lista_archivos)
        for idx, path in enumerate(lista_archivos):
            if not self.is_running: break
            
            nombre = os.path.basename(path)
            h = self.obtener_hash(path) if not path.endswith('.zip') else f"ZIP_{nombre}"
            
            if h not in self.archivo_indice: self.archivo_indice[h] = []
            self.archivo_indice[h].append(path)
            
            estado = "Duplicado" if len(self.archivo_indice[h]) > 1 else "OK"
            if estado == "Duplicado": self.total_duplicadas += 1
            self.total_encontradas += 1
            
            self.root.after(0, lambda p=path, e=estado: self.tree.insert("", "end", values=(os.path.basename(p), e, "Fuente")))
            
            # Progreso
            porcentaje = ((idx + 1) / total) * 100
            self.root.after(0, lambda v=porcentaje: self.progress.config(value=v))
            self.root.after(0, lambda: self.status_var.set(f"Fuentes: {self.total_encontradas} | Duplicados: {self.total_duplicadas}"))

        self.root.after(0, self.finalizar_proceso)

    def finalizar_proceso(self):
        self.is_running = False
        self.btn_auditar.config(state=tk.NORMAL)
        self.btn_cancelar.config(state=tk.DISABLED)
        messagebox.showinfo("Info", "Análisis completado.")

    def generar_reporte(self):
        if not self.archivo_indice:
            messagebox.showwarning("Aviso", "Primero analiza la carpeta.")
            return
            
        with open("reporte_fuentes_final.txt", "w", encoding="utf-8") as f:
            for h, paths in self.archivo_indice.items():
                estado = "DUPLICADO" if len(paths) > 1 else "OK"
                f.write(f"Estado: {estado} | Archivos: {paths}\n")
        
        messagebox.showinfo("Éxito", "Reporte guardado como: reporte_fuentes_final.txt")

if __name__ == "__main__":
    root = tk.Tk()
    app = GestorFuentesApp(root)
    root.mainloop()