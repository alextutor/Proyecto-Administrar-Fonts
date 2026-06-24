import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading, os, hashlib, shutil, json
from PIL import Image, ImageDraw, ImageFont, ImageTk

# Se implemento show_details y generar_preview para visualizar las fuentes

# Para garantizar una restauración precisa, vamos a implementar un sistema donde, al mover un archivo a 
#la papelera, generaremos un archivo .json complementario que almacene su ruta original.
# Actualización de delete_item y limpiar_duplicados 
#Diseño de la Ventana de Papelera Esta ventana incluirá una tabla para listar los archivos en la papelera y un botón de "Restaurar".
# abrir_ventana_papelera y restaurar_seleccion
#config_menu.add_command(label="Abrir Papelera", command=self.abrir_ventana_papelera)

class FontManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Profesional de Fuentes - V19 (Optimizado)")
        self.root.geometry("1200x950")
        
        self.is_running = False
        self.ruta_reporte = os.getcwd()
        self.papelera = os.path.join(os.getcwd(), "Papelera_Fuentes")
        if not os.path.exists(self.papelera): os.makedirs(self.papelera)
        self.whitelist_file = "whitelist.json"
        self.whitelist = self.cargar_whitelist()

        # --- MENÚ ---
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configuración", menu=config_menu)
        config_menu.add_command(label="Establecer Reportes", command=self.configurar_reporte)
        config_menu.add_command(label="Establecer Papelera", command=self.configurar_papelera)
        config_menu.add_command(label="Gestionar Lista Blanca", command=self.abrir_ventana_whitelist)
        config_menu.add_command(label="Abrir Papelera", command=self.abrir_ventana_papelera)

        # --- UI Layout ---
        top_frame = tk.Frame(root, padx=10, pady=5)
        top_frame.pack(fill=tk.X)
        self.path_entry = tk.Entry(top_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(top_frame, text="Carpeta Fuentes", command=self.browse).pack(side=tk.LEFT)

        paned = tk.PanedWindow(root, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Panel Superior
        top_panel = tk.Frame(paned)
        paned.add(top_panel, height=450)
        h_paned = tk.PanedWindow(top_panel, orient=tk.HORIZONTAL)
        h_paned.pack(fill=tk.BOTH, expand=True)

        list_frame = tk.Frame(h_paned)
        h_paned.add(list_frame, width=400)
        self.tree = self.crear_tabla(list_frame, "Fuentes", ["Nombre", "Ruta"])
        self.setup_context_menu(self.tree)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_details(self.tree))

        preview_frame = tk.Frame(h_paned)
        h_paned.add(preview_frame, width=800)
        tk.Label(preview_frame, text="Vista Previa", font=("Arial", 10, "bold")).pack(anchor="w")
        self.preview_lbl = tk.Label(preview_frame, text="Selecciona una fuente", bg="white", relief="sunken")
        self.preview_lbl.pack(fill=tk.BOTH, expand=True, pady=5)

        # Panel Inferior
        bot_panel = tk.Frame(paned)
        paned.add(bot_panel, height=200)
        self.tree_dup = self.crear_tabla(bot_panel, "Duplicados detectados", ["Nombre", "Ruta", "Duplicado de"])
        self.setup_context_menu(self.tree_dup)

        # --- BOTONES Y FOOTER ---
        path_info_frame = tk.Frame(root, padx=10, pady=5)
        path_info_frame.pack(fill=tk.X)
        tk.Label(path_info_frame, text="Ruta seleccionada:").pack(side=tk.LEFT)
        self.selected_path_var = tk.StringVar()
        tk.Entry(path_info_frame, textvariable=self.selected_path_var, state="readonly").pack(fill=tk.X, padx=5)

        btn_frame = tk.Frame(root, pady=10)
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Analizar", command=self.start_scan, bg="#d4edda").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Eliminar", command=self.delete_item, bg="#ffcccb").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Limpiar Duplicados", command=self.limpiar_duplicados, bg="#ffcccb").pack(side=tk.LEFT, padx=5)
        self.btn_cancel = tk.Button(btn_frame, text="Cancelar", command=self.stop_scan, bg="#f8d7da", state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(btn_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.lbl_percent = tk.Label(btn_frame, text="0%")
        self.lbl_percent.pack(side=tk.LEFT, padx=5)

    def crear_tabla(self, parent, titulo, columnas):
        tk.Label(parent, text=titulo, font=("Arial", 10, "bold")).pack(anchor="w")
        container = tk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar y Treeview integrados
        scroll = ttk.Scrollbar(container, orient="vertical")
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree = ttk.Treeview(container, columns=columnas, show='headings', yscrollcommand=scroll.set)
        scroll.config(command=tree.yview)
        
        for col in columnas: tree.heading(col, text=col)
        tree.column("Ruta", width=0, stretch=tk.NO)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        return tree

    def start_scan(self):
        # 1. Limpieza inmediata
        for t in [self.tree, self.tree_dup]:
            for i in t.get_children(): t.delete(i)
        
        # 2. Validación
        if not self.path_entry.get() or not os.path.isdir(self.path_entry.get()):
            messagebox.showwarning("Atención", "Por favor, selecciona una carpeta válida.")
            return

        self.is_running = True
        self.btn_cancel.config(state=tk.NORMAL)
        threading.Thread(target=self.scan_logic, daemon=True).start()

    def abrir_ventana_whitelist(self):
        win = tk.Toplevel(self.root)
        win.title("Gestión de Lista Blanca")
        win.geometry("600x500") # Tamaño aumentado
        
        tk.Label(win, text="Archivos y Carpetas protegidos", font=("Arial", 12, "bold")).pack(pady=10)
        lb = tk.Listbox(win, font=("Arial", 10))
        lb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for item in self.whitelist["archivos"] + self.whitelist["carpetas"]:
            lb.insert(tk.END, item)
            
        def borrar_sel():
            sel = lb.curselection()
            if sel:
                val = lb.get(sel[0])
                if val in self.whitelist["archivos"]: self.whitelist["archivos"].remove(val)
                if val in self.whitelist["carpetas"]: self.whitelist["carpetas"].remove(val)
                self.guardar_whitelist()
                lb.delete(sel[0])
        
        tk.Button(win, text="Eliminar selección de la Lista", command=borrar_sel, bg="#f8d7da").pack(pady=10)

    # ... (resto de métodos: scan_logic, get_hash, add_to_whitelist, etc., igual que en la versión anterior) ...
    def scan_logic(self):
        ruta = self.path_entry.get()
        seen = {}
        files = [os.path.join(r, f) for r, _, fs in os.walk(ruta) for f in fs if f.lower().endswith(('.ttf', '.otf'))]
        total = len(files)
        for i, f in enumerate(files):
            if not self.is_running: break
            if self.es_protegido(f): continue
            h = self.get_hash(f)
            percent = int(((i+1)/total)*100)
            if h in seen:
                self.root.after(0, lambda n=os.path.basename(f), p=f, o=seen[h]: self.tree_dup.insert("", "end", values=(n, p, o)))
            else: seen[h] = f
            self.root.after(0, lambda n=os.path.basename(f), p=f: self.tree.insert("", "end", values=(n, p)))
            self.root.after(0, lambda v=percent: [self.progress.config(value=v), self.lbl_percent.config(text=f"{v}%")])
        self.root.after(0, lambda: self.btn_cancel.config(state=tk.DISABLED))

    def get_hash(self, path):
        h = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""): h.update(chunk)
        return h.hexdigest()

    def es_protegido(self, path):
        if os.path.basename(path) in self.whitelist["archivos"]: return True
        for carpeta in self.whitelist["carpetas"]:
            if path.startswith(carpeta): return True
        return False

    def setup_context_menu(self, tree):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Proteger Archivo", command=lambda: self.add_to_whitelist("archivo"))
        menu.add_command(label="Proteger Carpeta", command=lambda: self.add_to_whitelist("carpeta"))
        tree.bind("<Button-3>", lambda e: menu.post(e.x_root, e.y_root))

    def add_to_whitelist(self, tipo):
        sel = self.tree.selection() or self.tree_dup.selection()
        if not sel: return
        tree = self.tree if self.tree.selection() else self.tree_dup
        path = tree.item(sel[0])['values'][1]
        if tipo == "archivo": self.whitelist["archivos"].append(os.path.basename(path))
        else: self.whitelist["carpetas"].append(os.path.dirname(path))
        self.guardar_whitelist()
        messagebox.showinfo("Hecho", "Elemento protegido.")

    def cargar_whitelist(self):
        if os.path.exists(self.whitelist_file):
            with open(self.whitelist_file, 'r') as f: return json.load(f)
        return {"archivos": [], "carpetas": []}

    def guardar_whitelist(self):
        with open(self.whitelist_file, 'w') as f: json.dump(self.whitelist, f)

    def delete_item(self):
        sel = self.tree.selection()
        if sel:
            path = self.tree.item(sel[0])['values'][1]
            nombre_archivo = os.path.basename(path)
            destino = os.path.join(self.papelera, nombre_archivo)
            
            # 1. Mover el archivo
            shutil.move(path, destino)
            
            # 2. Guardar metadatos en un archivo .json adjunto
            metadata = {
                "nombre": nombre_archivo,
                "ruta_original": path,
                "fecha_borrado": os.path.getmtime(destino) # O usar datetime.now()
            }
            with open(f"{destino}.json", 'w') as f:
                json.dump(metadata, f)
            
            self.tree.delete(sel[0])
            messagebox.showinfo("Éxito", f"Archivo movido a papelera con metadatos.")

    def limpiar_duplicados(self):
        for item in self.tree_dup.get_children():
            path = self.tree_dup.item(item)['values'][1]
            nombre = os.path.basename(path)
            destino = os.path.join(self.papelera, nombre)
            
            shutil.move(path, destino)
            
            # Guardar metadatos
            with open(f"{destino}.json", 'w') as f:
                json.dump({"ruta_original": path}, f)
                
            self.tree_dup.delete(item)
        messagebox.showinfo("Limpieza", "Duplicados movidos a la papelera con sus rutas originales.")

    def show_details(self, tree):
        sel = tree.selection()
        if sel:
            path = tree.item(sel[0])['values'][1]
            self.selected_path_var.set(path)
            
            # Actualizar la vista previa
            try:
                img_preview = self.generar_preview(path)
                self.preview_lbl.config(image=img_preview, text="")
                self.preview_lbl.image = img_preview # Evita que sea recolectado por el GC
            except Exception as e:
                self.preview_lbl.config(image='', text=f"No se pudo cargar la vista previa:\n{e}")
                
    def generar_preview(self, font_path):
        # Crear imagen con fondo blanco
        img = Image.new('RGB', (750, 150), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        try:
            # Cargar fuente con tamaño 40
            font = ImageFont.truetype(font_path, 40)
            text = "ABC abc 123 - Tipografía"
            # Centrar texto visualmente
            draw.text((20, 50), text, fill=(0, 0, 0), font=font)
        except Exception:
            # Fallback si no se puede renderizar
            draw.text((20, 50), "Error: Formato no soportado", fill=(255, 0, 0))
            
        return ImageTk.PhotoImage(img)
        
    def stop_scan(self): self.is_running = False
    def browse(self):
        d = filedialog.askdirectory()
        if d: self.path_entry.delete(0, tk.END); self.path_entry.insert(0, d)
    def configurar_reporte(self): self.ruta_reporte = filedialog.askdirectory()
    def configurar_papelera(self): self.papelera = filedialog.askdirectory()
    
    def abrir_ventana_papelera(self):
        win = tk.Toplevel(self.root)
        win.title("Gestor de Papelera")
        win.geometry("700x400")

        # Tabla de archivos en papelera
        cols = ("Nombre", "Ruta Original")
        tree = ttk.Treeview(win, columns=cols, show='headings')
        for col in cols: tree.heading(col, text=col)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Cargar archivos de la papelera
        for f in os.listdir(self.papelera):
            if f.endswith(".json"):
                with open(os.path.join(self.papelera, f), 'r') as j:
                    meta = json.load(j)
                    tree.insert("", "end", values=(meta.get("nombre", f), meta.get("ruta_original", "N/A")))

        def restaurar_seleccion():
            sel = tree.selection()
            if not sel: return
            
            item = tree.item(sel[0])['values']
            nombre = item[0]
            ruta_origen = item[1]
            
            # Mover de vuelta y borrar el JSON
            shutil.move(os.path.join(self.papelera, nombre), ruta_origen)
            os.remove(os.path.join(self.papelera, nombre + ".json"))
            
            tree.delete(sel[0])
            messagebox.showinfo("Restaurado", "El archivo ha vuelto a su ubicación original.")

        tk.Button(win, text="Restaurar Selección", command=restaurar_seleccion).pack(pady=10)
        

if __name__ == "__main__":
    root = tk.Tk()
    FontManagerApp(root)
    root.mainloop()