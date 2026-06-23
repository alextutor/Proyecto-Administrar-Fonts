import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading, os, hashlib, shutil, json
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont, ImageTk

class FontManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Profesional de Fuentes - V20 (Completo)")
        self.root.geometry("1200x950")
        
        self.is_running = False
        self.ruta_reporte = os.getcwd()
        self.papelera = os.path.join(os.getcwd(), "Papelera_Fuentes")
        if not os.path.exists(self.papelera): os.makedirs(self.papelera)
        self.whitelist_file = "whitelist.json"
        self.whitelist = self.cargar_whitelist()

        # Menú
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configuración", menu=config_menu)
        config_menu.add_command(label="Gestionar Lista Blanca", command=self.abrir_ventana_whitelist)

        # UI
        top_frame = tk.Frame(root, padx=10, pady=5)
        top_frame.pack(fill=tk.X)
        self.path_entry = tk.Entry(top_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(top_frame, text="Carpeta Fuentes", command=self.browse).pack(side=tk.LEFT)

        # Tabla Jerárquica
        container = tk.Frame(root, padx=10, pady=5)
        container.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(container, columns=("Ruta"), show='tree headings')
        self.tree.heading("#0", text="Familia / Archivo")
        self.tree.heading("Ruta", text="Ruta del archivo")
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Botones
        btn_frame = tk.Frame(root, pady=10)
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Analizar", command=self.start_scan, bg="#d4edda").pack(side=tk.LEFT, padx=5)
        self.btn_cancel = tk.Button(btn_frame, text="Cancelar", command=self.stop_scan, bg="#f8d7da")
        self.btn_cancel.pack(side=tk.LEFT, padx=5)
        self.progress = ttk.Progressbar(btn_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

    # Métodos de Lógica
    def cargar_whitelist(self):
        if os.path.exists(self.whitelist_file):
            with open(self.whitelist_file, 'r') as f: return json.load(f)
        return {"archivos": [], "carpetas": []}

    def guardar_whitelist(self):
        with open(self.whitelist_file, 'w') as f: json.dump(self.whitelist, f)

    def es_protegido(self, path):
        if os.path.basename(path) in self.whitelist["archivos"]: return True
        for carpeta in self.whitelist["carpetas"]:
            if path.startswith(carpeta): return True
        return False

    def obtener_familia(self, nombre_archivo):
        nombre = os.path.splitext(nombre_archivo)[0]
        if '-' in nombre: return nombre.split('-')[0]
        if ' ' in nombre: return nombre.split(' ')[0]
        return nombre

    def start_scan(self):
        # Limpieza de tabla
        for i in self.tree.get_children(): self.tree.delete(i)
        
        if not os.path.isdir(self.path_entry.get()):
            messagebox.showwarning("Error", "Carpeta inválida")
            return
            
        self.is_running = True
        threading.Thread(target=self.scan_logic, daemon=True).start()

    def scan_logic(self):
        ruta = self.path_entry.get()
        grupos = defaultdict(list)
        files = [os.path.join(r, f) for r, _, fs in os.walk(ruta) for f in fs if f.lower().endswith(('.ttf', '.otf'))]
        
        for f in files:
            if not self.is_running: break
            if self.es_protegido(f): continue
            
            familia = self.obtener_familia(os.path.basename(f))
            grupos[familia].append(f)

        # Dibujar árbol
        for familia, archivos in grupos.items():
            parent = self.tree.insert("", "end", text=familia, open=True)
            for path in archivos:
                self.tree.insert(parent, "end", text=os.path.basename(path), values=(path,))
        
        self.is_running = False

    def stop_scan(self): self.is_running = False
    def browse(self):
        d = filedialog.askdirectory()
        if d: self.path_entry.delete(0, tk.END); self.path_entry.insert(0, d)
        
    def abrir_ventana_whitelist(self):
        win = tk.Toplevel(self.root)
        win.title("Lista Blanca")
        lb = tk.Listbox(win)
        lb.pack(fill=tk.BOTH, expand=True)
        for item in self.whitelist["archivos"] + self.whitelist["carpetas"]: lb.insert(tk.END, item)

if __name__ == "__main__":
    root = tk.Tk()
    FontManagerApp(root)
    root.mainloop()