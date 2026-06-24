import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading, os, hashlib, shutil, json
from PIL import Image, ImageDraw, ImageFont, ImageTk
from datetime import datetime

class FontManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Profesional de Fuentes - V19 (Optimizado)")
        
        # 1. Definir dimensiones deseadas
        ancho = 1200
        alto = 850  # Compacto para asegurar visibilidad total con la barra de tareas
        
        # 2. Calcular posición con margen de seguridad
        pantalla_ancho = self.root.winfo_screenwidth()
        pantalla_alto = self.root.winfo_screenheight()
        margen_barra_tareas = 100

        x = (pantalla_ancho // 2) - (ancho // 2)
        y = ((pantalla_alto - margen_barra_tareas) // 2) - (alto // 2)    
        
        # 3. Aplicar geometría y vinculación de escape
        self.root.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.root.bind("<Escape>", lambda e: self.cerrar_con_confirmacion(e, self.root))
        
        self.is_running = False
        self.whitelist_file = "whitelist.json"
        self.whitelist = self.cargar_whitelist()
    
        #-----------Buscar Fuente ----------------
        self.all_items = [] # Guardaremos tuplas de (nombre, ruta) aquí
        #-----------Buscar Fuente ----------------
    
        # Cargamos configuración antes de crear la interfaz
        self.cargar_configuracion_json()
        if not os.path.exists(self.papelera): 
            os.makedirs(self.papelera)
    
    
        # --- MENÚ ---
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configuración", menu=config_menu)
        config_menu.add_command(label="Configuración General", command=self.abrir_ventana_configuracion)
        config_menu.add_command(label="Gestionar Lista Blanca", command=self.abrir_ventana_whitelist)
        config_menu.add_command(label="Abrir Papelera", command=self.abrir_ventana_papelera)

        # --- UI Layout ---
        top_frame = tk.Frame(root, padx=10, pady=5)
        top_frame.pack(fill=tk.X)
        self.path_entry = tk.Entry(top_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(top_frame, text="Carpeta Fuentes", command=self.browse).pack(side=tk.LEFT)

         # --- Buscador ---
        search_frame = tk.Frame(root, padx=10, pady=5)
        search_frame.pack(fill=tk.X)
        tk.Label(search_frame, text="Buscar fuente:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        # Usamos KeyRelease para que reaccione al borrar texto inmediatamente
        search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self.filtrar_fuentes())
        # --- Buscador ---

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
    
    def cerrar_con_confirmacion(self, event=None, ventana=None):
        win = ventana if ventana else self.root
        if messagebox.askokcancel("Confirmar", "¿Deseas cerrar esta ventana?", parent=win):
            win.destroy()  
            return "break"
        return "break"

    def centrar_ventana(self, win, ancho, alto):
        pantalla_ancho = win.winfo_screenwidth()
        pantalla_alto = win.winfo_screenheight()
        x = (pantalla_ancho // 2) - (ancho // 2)
        y = (pantalla_alto // 2) - (alto // 2)
        win.geometry(f"{ancho}x{alto}+{x}+{y}")

    def _preparar_modal(self, title, ancho, alto):
        """Método auxiliar para centralizar la configuración de ventanas secundarias"""
        win = tk.Toplevel(self.root)
        win.title(title)
        self.centrar_ventana(win, ancho, alto)
        win.transient(self.root)
        win.grab_set()
        win.attributes("-topmost", True)
        win.protocol("WM_DELETE_WINDOW", lambda: self.cerrar_con_confirmacion(None, win))
        win.bind("<Escape>", lambda e: self.cerrar_con_confirmacion(e, win))
        win.focus_set()
        return win
        
    def crear_tabla(self, parent, titulo, columnas):
        tk.Label(parent, text=titulo, font=("Arial", 10, "bold")).pack(anchor="w")
        container = tk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)
        
        scroll = ttk.Scrollbar(container, orient="vertical")
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree = ttk.Treeview(container, columns=columnas, show='headings', yscrollcommand=scroll.set)
        scroll.config(command=tree.yview)
        
        for col in columnas: 
            tree.heading(col, text=col)
        if "Ruta" in columnas:
            tree.column("Ruta", width=150, stretch=tk.YES)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        return tree

    def start_scan(self):
        for t in [self.tree, self.tree_dup]:
            for i in t.get_children(): t.delete(i)
        
        if not self.path_entry.get() or not os.path.isdir(self.path_entry.get()):
            messagebox.showwarning("Atención", "Por favor, selecciona una carpeta válida.")
            return

        self.is_running = True
        self.btn_cancel.config(state=tk.NORMAL)
        threading.Thread(target=self.scan_logic, daemon=True).start()

    def abrir_ventana_whitelist(self):
        win = self._preparar_modal("Gestión de Lista Blanca", 700, 400)
        
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

    def scan_logic(self):
        ruta = self.path_entry.get()
        seen = {}
        # Usamos list comprehension para obtener todas las fuentes
        files = [os.path.join(r, f) for r, _, fs in os.walk(ruta) for f in fs if f.lower().endswith(('.ttf', '.otf'))]
        total = len(files)
        
        if total == 0:
            self.root.after(0, lambda: [self.btn_cancel.config(state=tk.DISABLED), messagebox.showinfo("Búsqueda", "No se encontraron fuentes.")])
            return

        # Limpiamos el respaldo de la búsqueda al iniciar un nuevo escaneo
        self.all_items = [] 

        fuentes_batch = []
        duplicados_batch = []

        for i, f in enumerate(files):
            if not self.is_running: break
            if self.es_protegido(f): continue
                
            h = self.get_hash(f)
            nombre_b = os.path.basename(f)
            percent = int(((i + 1) / total) * 100)
            
            if h in seen:
                duplicados_batch.append(("", "end", (nombre_b, f, seen[h])))
            else:                 
                seen[h] = f
                # Solo agregamos al respaldo si es una fuente nueva (no duplicado)
                self.all_items.append((nombre_b, f)) 
                fuentes_batch.append(("", "end", (nombre_b, f)))

            # Inserción por lotes para mantener la UI fluida
            if len(fuentes_batch) >= 20 or i == total - 1:
                self.root.after(0, self._insertar_lotes, list(fuentes_batch), list(duplicados_batch), percent)
                fuentes_batch.clear()
                duplicados_batch.clear()

        # Finalización
        self.root.after(0, lambda: self.btn_cancel.config(state=tk.DISABLED))

    def _insertar_lotes(self, fuentes, duplicados, percent):
        """Inserta datos de forma masiva en la UI"""
        for f in fuentes:
            self.tree.insert(f[0], f[1], values=f[2])
        for d in duplicados:
            self.tree_dup.insert(d[0], d[1], values=d[2])
        self.progress.config(value=percent)
        self.lbl_percent.config(text=f"{percent}%")

    def get_hash(self, path):
        h = hashlib.md5()
        try:
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""): 
                    h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def es_protegido(self, path):
        if os.path.basename(path) in self.whitelist["archivos"]: return True
        for carpeta in self.whitelist["carpetas"]:
            if path.startswith(carpeta): return True
        return False

    def setup_context_menu(self, tree):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Proteger Archivo", command=lambda: self.add_to_whitelist("archivo", tree))
        menu.add_command(label="Proteger Carpeta", command=lambda: self.add_to_whitelist("carpeta", tree))
        tree.bind("<Button-3>", lambda e: menu.post(e.x_root, e.y_root))

    def add_to_whitelist(self, tipo, tree):
        sel = tree.selection()
        if not sel: return
        path = tree.item(sel[0])['values'][1]
        if tipo == "archivo": 
            self.whitelist["archivos"].append(os.path.basename(path))
        else: 
            self.whitelist["carpetas"].append(os.path.dirname(path))
        self.guardar_whitelist()
        messagebox.showinfo("Hecho", "Elemento protegido correctamente.")

    def cargar_whitelist(self):
        if os.path.exists(self.whitelist_file):
            with open(self.whitelist_file, 'r', encoding='utf-8') as f: 
                return json.load(f)
        return {"archivos": [], "carpetas": []}

    def guardar_whitelist(self):
        with open(self.whitelist_file, 'w', encoding='utf-8') as f: 
            json.dump(self.whitelist, f, indent=4)

    def _mover_a_papelera(self, path):
        """Helper para mover archivos y guardar un JSON con estructura unificada"""
        nombre_archivo = os.path.basename(path)
        destino = os.path.join(self.papelera, nombre_archivo)
        
        # Manejo si ya existe el archivo en la papelera para que no colisione
        if os.path.exists(destino):
            base, ext = os.path.splitext(nombre_archivo)
            destino = os.path.join(self.papelera, f"{base}_{int(datetime.now().timestamp())}{ext}")
            nombre_archivo = os.path.basename(destino)

        shutil.move(path, destino)
        
        metadata = {
            "nombre": nombre_archivo,
            "ruta_original": path,
            "fecha_borrado": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(f"{destino}.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4)

    def delete_item(self):
        sel = self.tree.selection()
        if not sel:
            return

        # 1. Obtenemos el path del elemento seleccionado
        path = self.tree.item(sel[0])['values'][1]
        
        # 2. Movemos el archivo a la papelera (lógica existente)
        self._mover_a_papelera(path)
        
        # 3. Borramos del Treeview visual
        self.tree.delete(sel[0])
        
        # 4. ACTUALIZACIÓN CRÍTICA: Borramos de la lista maestra self.all_items
        # Esto evita que al limpiar el buscador o filtrar de nuevo, 
        # el archivo borrado reaparezca en la lista.
        self.all_items = [item for item in self.all_items if item[1] != path]
        
        messagebox.showinfo("Éxito", "Archivo movido a papelera y eliminado de la lista.")

    def limpiar_duplicados(self):
        children = self.tree_dup.get_children()
        if not children:
            messagebox.showinfo("Limpieza", "No hay duplicados para limpiar.")
            return
            
        for item in children:
            path = self.tree_dup.item(item)['values'][1]
            if os.path.exists(path):
                self._mover_a_papelera(path)
            self.tree_dup.delete(item)
        messagebox.showinfo("Limpieza", "Todos los duplicados se movieron a la papelera.")

    def show_details(self, tree):
        sel = tree.selection()
        if sel:
            path = tree.item(sel[0])['values'][1]
            self.selected_path_var.set(path)
            try:
                img_preview = self.generar_preview(path)
                self.preview_lbl.config(image=img_preview, text="")
                self.preview_lbl.image = img_preview 
            except Exception as e:
                self.preview_lbl.config(image='', text=f"No se pudo cargar la vista previa:\n{e}")
                
    def generar_preview(self, font_path):
        img = Image.new('RGB', (750, 150), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(font_path, 34)
            text = "ABC abc 123 - Tipografía"
            draw.text((20, 50), text, fill=(0, 0, 0), font=font)
        except Exception:
            font_default = ImageFont.load_default()
            draw.text((20, 50), "Vista previa no disponible para este formato", fill=(255, 0, 0), font=font_default)
        return ImageTk.PhotoImage(img)
        
    def stop_scan(self): 
        self.is_running = False
        
    def browse(self):
        d = filedialog.askdirectory()
        if d: 
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, d)
    
    def abrir_ventana_papelera(self):
        win = self._preparar_modal("Gestor de Papelera", 750, 450)
    
        cols = ("Nombre", "Ruta Original")
        tree = ttk.Treeview(win, columns=cols, show='headings')
        for col in cols: 
            tree.heading(col, text=col)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Carga consistente de archivos de la papelera
        if os.path.exists(self.papelera):
            for f in os.listdir(self.papelera):
                if f.endswith(".json"):
                    try:
                        with open(os.path.join(self.papelera, f), 'r', encoding='utf-8') as j:
                            meta = json.load(j)
                            tree.insert("", "end", values=(meta.get("nombre", f[:-5]), meta.get("ruta_original", "N/A")))
                    except Exception:
                        pass

        def restaurar_seleccion():
            sel = tree.selection()
            if not sel: return
            
            item = tree.item(sel[0])['values']
            nombre = item[0]
            ruta_origen = item[1]
            
            archivo_papelera = os.path.join(self.papelera, nombre)
            archivo_json = archivo_papelera + ".json"
            
            if os.path.exists(archivo_papelera):
                # Validar y recrear el directorio de origen si fue borrado
                dir_origen = os.path.dirname(ruta_origen)
                if not os.path.exists(dir_origen):
                    os.makedirs(dir_origen, exist_ok=True)
                    
                shutil.move(archivo_papelera, ruta_origen)
                if os.path.exists(archivo_json):
                    os.remove(archivo_json)
                
                tree.delete(sel[0])
                messagebox.showinfo("Restaurado", "El archivo ha vuelto a su ubicación original.", parent=win)
            else:
                messagebox.showerror("Error", "No se encontró el archivo físico en la papelera.", parent=win)

        tk.Button(win, text="Restaurar Selección", command=restaurar_seleccion, bg="#d4edda").pack(pady=10)
        
    def abrir_ventana_configuracion(self):
        win = self._preparar_modal("Configuración General", 600, 250)
        win.columnconfigure(1, weight=1)

        # --- Fila 1: Reportes ---
        tk.Label(win, text="Ruta de Reportes:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        entry_reporte = tk.Entry(win)
        entry_reporte.insert(0, self.ruta_reporte)
        entry_reporte.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        tk.Button(win, text="Cambiar...", command=lambda: self.seleccionar_ruta(entry_reporte, True)).grid(row=0, column=2, padx=10, pady=10)

        # --- Fila 2: Papelera ---
        tk.Label(win, text="Ruta de Papelera:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        entry_papelera = tk.Entry(win)
        entry_papelera.insert(0, self.papelera)
        entry_papelera.grid(row=1, column=1, padx=5, pady=10, sticky="ew")
        tk.Button(win, text="Cambiar...", command=lambda: self.seleccionar_ruta(entry_papelera, True)).grid(row=1, column=2, padx=10, pady=10)

        # --- Botones inferiores ---
        btn_frame = tk.Frame(win)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=20)
        
        tk.Button(btn_frame, text="Guardar Cambios", command=lambda: self.guardar_y_cerrar(win, entry_reporte, entry_papelera), bg="#d4edda").pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Cancelar", command=win.destroy).pack(side=tk.LEFT, padx=10)

    def guardar_y_cerrar(self, win, entry_rep, entry_pap):
        self.ruta_reporte = entry_rep.get()
        self.papelera = entry_pap.get()
        
        # Aseguramos la existencia de la carpeta antes de guardar
        if not os.path.exists(self.papelera):
            os.makedirs(self.papelera, exist_ok=True)
        self.guardar_configuracion_json()
        
       # CORRECCIÓN: Pasamos 'parent=win' para que el messagebox 
        # bloquee específicamente a esta ventana y no se esconda detrás.
        messagebox.showinfo("Guardado", "Configuración actualizada.", parent=win)
        
        # Destruimos la ventana después de que el usuario acepta el mensaje
        win.destroy()

    def seleccionar_ruta(self, entry, es_carpeta=True):
        ruta = filedialog.askdirectory() if es_carpeta else filedialog.asksaveasfilename()
        if ruta:
            entry.delete(0, tk.END)
            entry.insert(0, ruta)   

    def guardar_configuracion_json(self):
        config = {
            "ruta_reporte": self.ruta_reporte,
            "papelera": self.papelera
        }
        with open("config.json", "w", encoding='utf-8') as f:
            json.dump(config, f, indent=4)

    def cargar_configuracion_json(self):
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding='utf-8') as f:
                    config = json.load(f)
                    self.ruta_reporte = config.get("ruta_reporte", os.getcwd())
                    self.papelera = config.get("papelera", os.path.join(os.getcwd(), "Papelera_Fuentes"))
            except Exception:
                self.ruta_reporte = os.getcwd()
                self.papelera = os.path.join(os.getcwd(), "Papelera_Fuentes")
        else:
            self.ruta_reporte = os.getcwd()
            self.papelera = os.path.join(os.getcwd(), "Papelera_Fuentes")
            
    
    def filtrar_fuentes(self, *args):
        query = self.search_var.get().lower()
        
        # 1. Limpiamos totalmente el Treeview visual
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # 2. Reinsertamos solo lo que cumple con el filtro
        for nombre, ruta in self.all_items:
            # Si el query está vacío (busqueda limpia) O si el nombre coincide
            if not query or query in nombre.lower():
                self.tree.insert("", "end", values=(nombre, ruta))
            
            
if __name__ == "__main__":
    root = tk.Tk()
    app = FontManagerApp(root)
    root.mainloop()