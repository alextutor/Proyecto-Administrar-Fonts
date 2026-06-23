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
        self.root.geometry("1200x750") # Aumentamos el tamaño base de la ventana
        
        self.archivo_indice = {} 
        self.is_running = False
        self.papelera_path = os.path.join(os.getcwd(), "Papelera_Fuentes")
        if not os.path.exists(self.papelera_path): os.makedirs(self.papelera_path)

        # --- UI: Top ---
        frame_top = tk.LabelFrame(root, text="Configuración")
        frame_top.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(frame_top, text="Carpeta de Fuentes:").pack(side=tk.LEFT, padx=5)
        self.entry_ruta = tk.Entry(frame_top)
        self.entry_ruta.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(frame_top, text="Seleccionar", command=self.seleccionar_carpeta).pack(side=tk.LEFT, padx=5)

        # --- UI: Centro (Tabla + Preview) ---
        frame_mid = tk.Frame(root)
        frame_mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Tabla
        self.tree = ttk.Treeview(frame_mid, columns=("Ruta", "Estado", "Tipo", "Fullpath"), show='headings')
        self.tree.heading("Ruta", text="Nombre del Archivo")
        self.tree.heading("Estado", text="Estado")
        self.tree.heading("Tipo", text="Formato")
        self.tree.column("Fullpath", width=0, stretch=tk.NO)
        self.tree.column("Ruta", width=400)
        
        scrollbar = ttk.Scrollbar(frame_mid, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.previsualizar_fuente)

        # Panel Preview mejorado: ancho aumentado y expansión permitida
        self.lbl_preview = tk.Label(frame_mid, text="Vista Previa", bg="#f0f0f0", width=60, relief="sunken")
        self.lbl_preview.pack(side=tk.RIGHT, padx=10, fill=tk.BOTH, expand=False)

        # --- UI: Bottom ---
        frame_bottom = tk.Frame(root)
        frame_bottom.pack(fill=tk.X, padx=10, pady=10)

        self.btn_auditar = tk.Button(frame_bottom, text="2. Recorrer y Analizar Fuentes", command=self.iniciar_auditoria, bg="#c8e6c9")
        self.btn_auditar.pack(side=tk.LEFT, padx=5)
        self.btn_reporte = tk.Button(frame_bottom, text="Generar Reporte TXT", command=self.generar_reporte, bg="#bbdefb")
        self.btn_reporte.pack(side=tk.LEFT, padx=5)
        self.btn_borrar = tk.Button(frame_bottom, text="Borrar Seleccionado", command=self.borrar_seleccionado, bg="#ffcc80")
        self.btn_borrar.pack(side=tk.LEFT, padx=5)
        self.btn_cancelar = tk.Button(frame_bottom, text="Cancelar", command=self.cancelar_proceso, bg="#ffcdd2", state=tk.DISABLED)
        self.btn_cancelar.pack(side=tk.LEFT, padx=5)

        self.progress = ttk.Progressbar(frame_bottom, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        self.status_var = tk.StringVar(value="Listo.")
        self.lbl_status = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

    # --- Lógica ---
    def obtener_hash(self, ruta_archivo):
        hasher = hashlib.md5()
        try:
            with open(ruta_archivo, 'rb') as f:
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
            return hasher.hexdigest()
        except: return "ERROR"

    def previsualizar_fuente(self, event):
        selected = self.tree.selection()
        if not selected: return
        
        path = self.tree.item(selected[0])['values'][3]
        if not path or not path.lower().endswith(('.ttf', '.otf')):
            self.lbl_preview.config(text="Formato no compatible con vista previa")
            return

        try:
            # Creamos una imagen más ancha (400px) para aprovechar el nuevo espacio
            img = Image.new('RGB', (400, 200), color=(255, 255, 255))
            d = ImageDraw.Draw(img)
            fnt = ImageFont.truetype(path, 35)
            d.text((10, 50), "AaBbCc 12345", font=fnt, fill=(0, 0, 0))
            
            img_tk = ImageTk.PhotoImage(img)
            self.lbl_preview.config(image=img_tk, text="")
            self.lbl_preview.image = img_tk
        except Exception:
            self.lbl_preview.config(text="Error al renderizar fuente")

    def borrar_seleccionado(self):
        selected = self.tree.selection()
        if not selected: return
        path = self.tree.item(selected[0])['values'][3]
        if messagebox.askyesno("Confirmar", "¿Mover a la papelera?"):
            try:
                shutil.move(path, os.path.join(self.papelera_path, os.path.basename(path)))
                self.tree.delete(selected[0])
                messagebox.showinfo("Hecho", "Archivo movido a Papelera_Fuentes")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo mover el archivo: {e}")

    def seleccionar_carpeta(self):
        ruta = filedialog.askdirectory()
        if ruta:
            self.entry_ruta.delete(0, tk.END)
            self.entry_ruta.insert(0, ruta)

    def cancelar_proceso(self):
        self.is_running = False

    def iniciar_auditoria(self):
        ruta = self.entry_ruta.get()
        if not os.path.exists(ruta): return
        
        self.is_running = True
        self.archivo_indice = {}
        for i in self.tree.get_children(): self.tree.delete(i)
        
        self.btn_auditar.config(state=tk.DISABLED)
        self.btn_cancelar.config(state=tk.NORMAL)
        threading.Thread(target=self.ejecutar_analisis, args=(ruta,), daemon=True).start()

    def ejecutar_analisis(self, ruta):
        lista = []
        for root, _, files in os.walk(ruta):
            for f in files:
                if f.lower().endswith(('.ttf', '.otf', '.pfb', '.pfm', '.zip')):
                    lista.append(os.path.join(root, f))
        
        total = len(lista)
        for idx, path in enumerate(lista):
            if not self.is_running: break
            h = self.obtener_hash(path) if not path.endswith('.zip') else f"ZIP_{os.path.basename(path)}"
            if h not in self.archivo_indice: self.archivo_indice[h] = []
            self.archivo_indice[h].append(path)
            
            estado = "Duplicado" if len(self.archivo_indice[h]) > 1 else "OK"
            self.root.after(0, lambda p=path, e=estado: self.tree.insert("", "end", values=(os.path.basename(p), e, "Fuente", p)))
            
            porcentaje = ((idx + 1) / total) * 100
            self.root.after(0, lambda v=porcentaje: self.progress.config(value=v))
            self.root.after(0, lambda i=idx+1: self.status_var.set(f"Procesando {i}/{total}"))

        self.root.after(0, self.finalizar_proceso)

    def finalizar_proceso(self):
        self.is_running = False
        self.btn_auditar.config(state=tk.NORMAL)
        self.btn_cancelar.config(state=tk.DISABLED)
        messagebox.showinfo("Info", "Análisis completado.")

    def generar_reporte(self):
        with open("reporte_fuentes_final.txt", "w", encoding="utf-8") as f:
            for h, paths in self.archivo_indice.items():
                f.write(f"Paths: {paths}\n")
        messagebox.showinfo("Éxito", "Reporte guardado.")

if __name__ == "__main__":
    root = tk.Tk()
    app = GestorFuentesApp(root)
    root.mainloop()