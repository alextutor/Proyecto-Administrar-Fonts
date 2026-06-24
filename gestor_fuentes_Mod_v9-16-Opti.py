# ---------------Coleccion -----------------------
# 1) deseo centrar el formulario secundario añadir coleccion utilizando la funcion def centrar_ventana
# 2) Poner otro boton analizar al costado del check incluir subcarpeta
# 3) y en el formulario secundario configuracion General al presionar el boton cambiar la ventana seleccionar carpeta se va detras del formulariuo secundario 
# 2. 🗂️ Creación de Colecciones o "Etiquetas" Virtuales (Categorías)
# ¿Qué hace?: Permitir agrupar fuentes por estilos (por ejemplo: Serif, Sans-Serif, Cursivas, Corporativas, Títulos) sin necesidad de mover físicamente los archivos de carpeta.
# ¿Cómo se implementaría?: Una base de datos ligera o un archivo JSON secundario (colecciones.json) donde se asocien las rutas de las fuentes a etiquetas creadas por ti, añadiendo un filtro en la UI para ver solo una colección.



import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser
import threading, os, hashlib, shutil, json, sys
from PIL import Image, ImageDraw, ImageFont, ImageTk
from datetime import datetime
import ctypes
from ctypes import wintypes
import winreg

# Constantes de la API de Windows para fuentes
WM_FONTCHANGE = 0x001D
HWND_BROADCAST = 0xFFFF

class FontManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Profesional de Fuentes - V20.0 (Instalación por Lotes)")
        
        # 1. Definir dimensiones deseadas
        ancho = 1350 
        alto = 850
        
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
        
        # Control de fuentes activadas temporalmente en esta sesión
        self.fuentes_temporales = set()
    
        # Variables de control para la vista previa interactiva
        self.preview_dark_mode = False  
        self.font_size_var = tk.IntVar(value=32)  
        self.current_bg_color = "#ffffff"
        self.current_text_color = "#000000"
    
        self.all_items = [] 
    
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
        config_menu.add_separator()
        config_menu.add_command(label="📊 Exportar Reporte de Fuentes", command=self.exportar_reporte)
        
        #------------- Coleccion ------------------------
        # Dentro de tu función setup_context_menu:
        config_menu.add_command(label="📁 Añadir a Colección", command=self.añadir_a_coleccion)
        #------------- Coleccion ------------------------

        # --- UI Layout ---
        top_frame = tk.Frame(root, padx=10, pady=5)
        top_frame.pack(fill=tk.X)
        self.path_entry = tk.Entry(top_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Botones de selección de carpetas
        tk.Button(top_frame, text="Carpeta Fuentes", command=self.browse).pack(side=tk.LEFT, padx=2)
        tk.Button(top_frame, text="🏛️ Fuentes del Sistema", command=self.seleccionar_fuentes_sistema, bg="#e2e8f0").pack(side=tk.LEFT, padx=2)
        
        # Checkbox para controlar la búsqueda recursiva en subcarpetas
        self.buscar_subcarpetas_var = tk.BooleanVar(value=True)
        self.chk_subcarpetas = tk.Checkbutton(top_frame, text="Incluir subcarpetas", variable=self.buscar_subcarpetas_var)
        self.chk_subcarpetas.pack(side=tk.LEFT, padx=5)

        # Nuevo botón Analizar al costado
        tk.Button(top_frame, text="🔍 Analizar", command=self.start_scan, bg="#d4edda").pack(side=tk.LEFT, padx=5)


        # --- Buscador y Filtros ---
        search_frame = tk.Frame(root, padx=10, pady=5)
        search_frame.pack(fill=tk.X)
        tk.Label(search_frame, text="Buscar fuente:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_entry.bind("<KeyRelease>", lambda e: self.filtrar_fuentes())
        
        tk.Label(search_frame, text="Filtrar por Estado:").pack(side=tk.LEFT, padx=(10, 5))
        self.filtro_estado_var = tk.StringVar(value="Todas")
        self.cb_filtro_estado = ttk.Combobox(search_frame, textvariable=self.filtro_estado_var, values=["Todas", "Instaladas", "Temporales", "No Instaladas"], state="readonly", width=15)
        self.cb_filtro_estado.pack(side=tk.LEFT, padx=5)
        self.cb_filtro_estado.bind("<<ComboboxSelected>>", lambda e: self.filtrar_fuentes())
        
        # ---------------Coleccion ----------------------- 
        
        tk.Label(search_frame, text="Colección:").pack(side=tk.LEFT, padx=(10, 5))
        self.coleccion_var = tk.StringVar(value="Todas")
        self.colecciones = self.cargar_colecciones()
        self.cb_coleccion = ttk.Combobox(search_frame, textvariable=self.coleccion_var, values=["Todas"] + list(self.colecciones.keys()), state="readonly", width=15)
        self.cb_coleccion.pack(side=tk.LEFT, padx=5)
        self.cb_coleccion.bind("<<ComboboxSelected>>", lambda e: self.filtrar_fuentes())
        # ---------------Coleccion -----------------------
        

        paned = tk.PanedWindow(root, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Panel Superior
        top_panel = tk.Frame(paned)
        paned.add(top_panel, height=450)
        h_paned = tk.PanedWindow(top_panel, orient=tk.HORIZONTAL)
        h_paned.pack(fill=tk.BOTH, expand=True)

        list_frame = tk.Frame(h_paned)
        h_paned.add(list_frame, width=450)
        self.tree = self.crear_tabla(list_frame, "Fuentes", ["Nombre", "Estado", "Ruta"])
        
        # Configurar colores visuales mediante Tags en el Treeview
        self.tree.tag_configure("instalada", background="#d4edda", foreground="#155724")
        self.tree.tag_configure("temporal", background="#ffe8cc", foreground="#d97706")
        self.tree.tag_configure("normal", background="white", foreground="black")
        
        self.setup_context_menu(self.tree)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_details(self.tree))

        # Panel derecho superior (Contenedor de Vista Previa)
        preview_frame = tk.Frame(h_paned)
        h_paned.add(preview_frame, width=850)
        
        preview_top_bar = tk.Frame(preview_frame, pady=2)
        preview_top_bar.pack(fill=tk.X, anchor="w")
        
        # --- GRUPO IZQUIERDO ---
        basic_group = tk.Frame(preview_top_bar)
        basic_group.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        tk.Label(basic_group, text="Texto:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(5, 2))
        self.custom_text_var = tk.StringVar()
        self.custom_text_entry = tk.Entry(basic_group, textvariable=self.custom_text_var, font=("Arial", 10), width=22)
        self.custom_text_entry.pack(side=tk.LEFT, padx=5)
        self.custom_text_entry.bind("<KeyRelease>", lambda e: self.show_details(self.tree))

        tk.Label(basic_group, text="Tamaño:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(5, 2))
        self.cb_size = ttk.Combobox(basic_group, textvariable=self.font_size_var, values=[12, 16, 20, 24, 28, 32, 36, 42, 48, 56, 72, 96, 120], state="readonly", width=4)
        self.cb_size.pack(side=tk.LEFT, padx=2)
        self.cb_size.bind("<<ComboboxSelected>>", lambda e: self.show_details(self.tree))

        self.btn_mode = tk.Button(basic_group, text="☀️ Modo Claro", command=self.toggle_preview_mode, width=12, bg="#f1f5f9")
        self.btn_mode.pack(side=tk.LEFT, padx=5)

        # --- GRUPO DERECHO ---
        adv_group = tk.LabelFrame(preview_top_bar, text="🎨 Personalización Avanzada", padx=5, pady=2)
        adv_group.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        tk.Label(adv_group, text="Ajuste:", font=("Arial", 8)).pack(side=tk.LEFT)
        self.slider_size = ttk.Scale(adv_group, from_=10, to=150, orient=tk.HORIZONTAL, variable=self.font_size_var, command=lambda e: self.show_details(self.tree))
        self.slider_size.pack(side=tk.LEFT, padx=5)

        self.btn_color_text = tk.Button(adv_group, text="🔤 Texto", command=self.choose_text_color, bg="#e2e8f0", width=6)
        self.btn_color_text.pack(side=tk.LEFT, padx=2)

        self.btn_color_bg = tk.Button(adv_group, text="🔲 Fondo", command=self.choose_bg_color, bg="#e2e8f0", width=6)
        self.btn_color_bg.pack(side=tk.LEFT, padx=2)

        self.btn_invert = tk.Button(adv_group, text="🔄 Invertir", command=self.invert_colors, bg="#e2e8f0")
        self.btn_invert.pack(side=tk.LEFT, padx=2)

        self.btn_default = tk.Button(adv_group, text="⏮ Default", command=self.default_colors, bg="#e2e8f0")
        self.btn_default.pack(side=tk.LEFT, padx=2)

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
        tk.Button(btn_frame, text="🔍 Analizar", command=self.start_scan, bg="#d4edda").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Eliminar Archivo", command=self.delete_item, bg="#ffcccb").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Limpiar Duplicados", command=self.limpiar_duplicados, bg="#ffcccb").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Desactivar Temporales", command=self.desactivar_todas_las_temporales, bg="#ffe8cc", fg="#d97706", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="📊 Exportar Reporte", command=self.exportar_reporte, bg="#ffe8cc", fg="#d97706", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
             
        self.btn_cancel = tk.Button(btn_frame, text="Cancelar Scan", command=self.stop_scan, bg="#f8d7da", state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(btn_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.lbl_percent = tk.Label(btn_frame, text="0%")
        self.lbl_percent.pack(side=tk.LEFT, padx=5)

    def choose_text_color(self):
        color_code = colorchooser.askcolor(title="Elegir color de texto", initialcolor=self.current_text_color)[1]
        if color_code:
            self.current_text_color = color_code
            self.show_details(self.tree)

    def choose_bg_color(self):
        color_code = colorchooser.askcolor(title="Elegir color de fondo", initialcolor=self.current_bg_color)[1]
        if color_code:
            self.current_bg_color = color_code
            self.show_details(self.tree)

    def invert_colors(self):
        self.current_text_color, self.current_bg_color = self.current_bg_color, self.current_text_color
        self.show_details(self.tree)

    def default_colors(self):
        if self.preview_dark_mode:
            self.current_bg_color = "#1e293b"
            self.current_text_color = "#ffffff"
        else:
            self.current_bg_color = "#ffffff"
            self.current_text_color = "#000000"
        self.show_details(self.tree)

    def toggle_preview_mode(self):
        self.preview_dark_mode = not self.preview_dark_mode
        if self.preview_dark_mode:
            self.btn_mode.config(text="🌙 Modo Oscuro", bg="#1e293b", fg="white")
            self.current_bg_color = "#1e293b"
            self.current_text_color = "#ffffff"
        else:
            self.btn_mode.config(text="☀️ Modo Claro", bg="#f1f5f9", fg="black")
            self.current_bg_color = "#ffffff"
            self.current_text_color = "#000000"
        self.show_details(self.tree)

    def exportar_reporte(self):
        if not self.all_items:
            messagebox.showwarning("Atención", "No hay datos para exportar. Por favor, realice un análisis analizando una carpeta primero.")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Guardar Reporte de Fuentes Analizadas",
            defaultextension=".csv",
            filetypes=[
                ("Archivo CSV (*.csv)", "*.csv"),
                ("Reporte HTML (*.html)", "*.html"),
                ("Documento de Texto (*.txt)", "*.txt")
            ]
        )
        
        if not file_path:
            return
            
        ext = os.path.splitext(file_path)[1].lower()
        ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            if ext == ".csv":
                import csv
                with open(file_path, mode='w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f, delimiter=',')
                    writer.writerow(["Nombre de la Fuente", "Estado Actual", "Ruta Absoluta del Archivo"])
                    for nombre, estado, ruta in self.all_items:
                        writer.writerow([nombre, estado, ruta])
                        
            elif ext == ".html":
                with open(file_path, mode='w', encoding='utf-8') as f:
                    f.write(f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte Avanzado de Fuentes</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 30px; background-color: #f8fafc; color: #334155; }}
        h1 {{ color: #0f172a; margin-bottom: 5px; font-size: 24px; }}
        .meta-info {{ font-size: 14px; color: #64748b; margin-bottom: 25px; }}
        table {{ width: 100%; border-collapse: collapse; background: #ffffff; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px 16px; text-align: left; font-size: 14px; }}
        th {{ background-color: #1e293b; color: #ffffff; font-weight: 600; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; }}
        tr {{ border-bottom: 1px solid #e2e8f0; }}
        tr:last-child {{ border-bottom: none; }}
        tr:hover {{ background-color: #f1f5f9; }}
        .badge {{ padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; display: inline-block; }}
        .instalada {{ background-color: #d4edda; color: #155724; }}
        .temporal {{ background-color: #ffe8cc; color: #d97706; }}
        .no-instalada {{ background-color: #e2e8f0; color: #475569; }}
    </style>
</head>
<body>
    <h1>📋 Inventario y Reporte de Fuentes</h1>
    <div class="meta-info">
        <strong>Fecha de generación:</strong> {ahora_str}<br>
        <strong>Total de elementos listados:</strong> {len(self.all_items)} fuentes únicas
    </div>
    <table>
        <thead>
            <tr>
                <th>Nombre del Archivo</th>
                <th>Estado del Sistema</th>
                <th>Ubicación en Disco</th>
            </tr>
        </thead>
        <tbody>
""")
                    for nombre, estado, ruta in self.all_items:
                        badge_class = "no-instalada"
                        if estado == "Instalada": badge_class = "instalada"
                        elif estado == "Temporal": badge_class = "temporal"
                        
                        f.write(f"""            <tr>
                <td style="font-weight: 500;">{nombre}</td>
                <td><span class="badge {badge_class}">{estado}</span></td>
                <td style="color: #64748b; font-family: monospace; font-size: 13px;">{ruta}</td>
            </tr>\n""")
                    f.write("""        </tbody>
    </table>
</body>
</html>
""")
            else: 
                with open(file_path, mode='w', encoding='utf-8') as f:
                    f.write(f"================================================================================\n")
                    f.write(f"                   REPORTE DE INVENTARIO DE FUENTES TIPOGRÁFICAS                \n")
                    f.write(f"================================================================================\n")
                    f.write(f"Fecha de Generación: {ahora_str}\n")
                    f.write(f"Total Fuentes Únicas: {len(self.all_items)}\n")
                    f.write(f"--------------------------------------------------------------------------------\n\n")
                    f.write(f"{'NOMBRE DEL ARCHIVO':<45} | {'ESTADO':<15} | RUTA EN DISCO\n")
                    f.write(f"{'-'*45}-|-{'-'*15}-|-{'-'*50}\n")
                    for nombre, estado, ruta in self.all_items:
                        f.write(f"{nombre:<45} | {estado:<15} | {ruta}\n")
                        
            messagebox.showinfo("Éxito", f"¡Reporte generado con éxito!\n\nGuardado en:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error de Escritura", f"No se pudo guardar el archivo del reporte:\n{e}")

    def seleccionar_fuentes_sistema(self):
        ruta_sistema = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Fonts')
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, ruta_sistema)
        
    def es_administrador(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def obtener_estado_fuente(self, ruta_archivo):
        nombre_base = os.path.basename(ruta_archivo)
        if ruta_archivo in self.fuentes_temporales:
            return "Temporal"
            
        ruta_sistema = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Fonts', nombre_base)
        if os.path.exists(ruta_sistema):
            return "Instalada"
            
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts", 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    nombre_fuente, valor_fuente, _ = winreg.EnumValue(key, i)
                    if nombre_base.lower() == str(valor_fuente).lower():
                        return "Instalada"
                    i += 1
        except OSError:
            pass
            
        return "No Instalada"

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
        
        tree = ttk.Treeview(container, columns=columnas, show='headings', yscrollcommand=scroll.set, selectmode="extended")
        scroll.config(command=tree.yview)
        
        for col in columnas: 
            tree.heading(col, text=col)
        if "Ruta" in columnas:
            tree.column("Ruta", width=150, stretch=tk.YES)
        if "Estado" in columnas:
            tree.column("Estado", width=100, anchor="center")
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
        lb = tk.Listbox(win, font=("Arial", 10), selectmode=tk.EXTENDED)
        lb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for item in self.whitelist["archivos"] + self.whitelist["carpetas"]:
            lb.insert(tk.END, item)
            
        def borrar_sel():
            sel = lb.curselection()
            if sel:
                for idx in reversed(sel):
                    val = lb.get(idx)
                    if val in self.whitelist["archivos"]: self.whitelist["archivos"].remove(val)
                    if val in self.whitelist["carpetas"]: self.whitelist["carpetas"].remove(val)
                    lb.delete(idx)
                self.guardar_whitelist()
        
        tk.Button(win, text="Eliminar selección de la Lista", command=borrar_sel, bg="#f8d7da").pack(pady=10)

    def scan_logic(self):
        ruta = self.path_entry.get()
        seen = {}
        
        try:
            if self.buscar_subcarpetas_var.get():
                files = [os.path.join(r, f) for r, _, fs in os.walk(ruta) for f in fs if f.lower().endswith(('.ttf', '.otf'))]
            else:
                files = [os.path.join(ruta, f) for f in os.listdir(ruta) if os.path.isfile(os.path.join(ruta, f)) and f.lower().endswith(('.ttf', '.otf'))]
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"No se pudo leer la carpeta:\n{e}"))
            self.root.after(0, lambda: self.btn_cancel.config(state=tk.DISABLED))
            return
            
        total = len(files)
        if total == 0:
            self.root.after(0, lambda: [self.btn_cancel.config(state=tk.DISABLED), messagebox.showinfo("Búsqueda", "No se encontraron fuentes.")])
            return

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
                estado = self.obtener_estado_fuente(f)
                self.all_items.append((nombre_b, estado, f)) 
                fuentes_batch.append(("", "end", (nombre_b, estado, f)))

            if len(fuentes_batch) >= 20 or i == total - 1:
                self.root.after(0, self._insertar_lotes, list(fuentes_batch), list(duplicados_batch), percent)
                fuentes_batch.clear()
                duplicados_batch.clear()

        self.root.after(0, lambda: self.btn_cancel.config(state=tk.DISABLED))

    def _insertar_lotes(self, fuentes, duplicados, percent):
        for f in fuentes:
            tag = "normal"
            if f[2][1] == "Instalada": tag = "instalada"
            elif f[2][1] == "Temporal": tag = "temporal"
            self.tree.insert(f[0], f[1], values=f[2], tags=(tag,))
            
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
        menu.add_command(label="⚡ Activar temporalmente (Masivo)", command=lambda: self.activar_temporal_ctx(tree))
        menu.add_command(label="💾 Instalar permanentemente (Masivo)", command=lambda: self.instalar_permanente_ctx(tree))
        menu.add_command(label="❌ Desinstalar del Sistema (Masivo)", command=lambda: self.desinstalar_sistema_ctx(tree))
        menu.add_separator()
        menu.add_command(label="Proteger Archivo(s)", command=lambda: self.add_to_whitelist("archivo", tree))
        menu.add_command(label="Proteger Carpeta(s)", command=lambda: self.add_to_whitelist("carpeta", tree))
        
        #------------- Coleccion ------------------------
        menu.add_command(label="📁 Añadir a Colección", command=self.añadir_a_coleccion)
        #------------- Coleccion ------------------------

        
        
        def post_menu(e):
            item = tree.identify_row(e.y)
            if item:
                # Mantiene la selección múltiple intacta si haces clic sobre algo ya seleccionado
                if item not in tree.selection():
                    tree.selection_set(item)
                menu.post(e.x_root, e.y_root)
                
        tree.bind("<Button-3>", post_menu)
        
    # --- LÓGICA DE PROCESAMIENTO POR LOTES (BATCH) ---
    def _procesar_lote(self, accion_nombre, seleccion, tree, func_accion):
        total = len(seleccion)
        if total == 0: return
        
        # Ventana de progreso visual
        win = self._preparar_modal(f"Procesando: {accion_nombre}", 450, 150)
        tk.Label(win, text=f"Procesando {total} elementos...", font=("Arial", 11, "bold")).pack(pady=(15, 5))
        
        prog = ttk.Progressbar(win, mode='determinate', maximum=total)
        prog.pack(fill=tk.X, padx=20, pady=10)
        
        lbl_estado = tk.Label(win, text="Iniciando...", font=("Arial", 9), fg="#666666")
        lbl_estado.pack(fill=tk.X, padx=10)
        
        exitos = 0
        errores = 0
        
        for i, item in enumerate(seleccion):
            valores = tree.item(item)['values']
            path = valores[2] if len(valores) > 2 else valores[1]
            
            lbl_estado.config(text=f"[{i+1}/{total}] {os.path.basename(path)}")
            win.update() 
            
            if func_accion(path):
                exitos += 1
            else:
                errores += 1
                
            prog['value'] = i + 1
        
        # Transmisión a Windows SOLO UNA VEZ al final del lote entero
        if exitos > 0:
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
            self.filtrar_fuentes()
            
        win.destroy()
        messagebox.showinfo("Operación por Lotes Finalizada", f"{accion_nombre} completada.\n\n✅ Éxitos: {exitos}\n❌ Errores u omitidos: {errores}")

    # Funciones individuales de trabajo para el lote
    def _activar_una_temporal(self, path):
        if not os.path.exists(path): return False
        if path in self.fuentes_temporales: return True
        if ctypes.windll.gdi32.AddFontResourceW(path) != 0:
            self.fuentes_temporales.add(path)
            self.actualizar_item_maestro(path, "Temporal")
            return True
        return False

    def _instalar_una_permanente(self, path):
        if not os.path.exists(path): return False
        nombre_archivo = os.path.basename(path)
        ruta_destino = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Fonts', nombre_archivo)
        try:
            if not os.path.exists(ruta_destino):
                shutil.copy(path, ruta_destino)
            font_title = os.path.splitext(nombre_archivo)[0] + " (TrueType)"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts", 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, font_title, 0, winreg.REG_SZ, nombre_archivo)
            except Exception:
                pass
            ctypes.windll.gdi32.AddFontResourceW(ruta_destino)
            self.actualizar_item_maestro(path, "Instalada")
            return True
        except Exception:
            return False

    def _desinstalar_una_sistema(self, path):
        nombre_archivo = os.path.basename(path)
        exito = False
        if path in self.fuentes_temporales:
            ctypes.windll.gdi32.RemoveFontResourceW(path)
            self.fuentes_temporales.discard(path)
            exito = True
            
        ruta_sistema = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Fonts', nombre_archivo)
        try:
            if os.path.exists(ruta_sistema):
                ctypes.windll.gdi32.RemoveFontResourceW(ruta_sistema)
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts", 0, winreg.KEY_ALL_ACCESS) as key:
                    i = 0
                    while True:
                        nombre_fuente, valor_fuente, _ = winreg.EnumValue(key, i)
                        if str(valor_fuente).lower() == nombre_archivo.lower():
                            winreg.DeleteValue(key, nombre_fuente)
                            break
                        i += 1
            except OSError:
                pass
            if os.path.exists(ruta_sistema):
                os.remove(ruta_sistema)
            self.actualizar_item_maestro(path, "No Instalada")
            exito = True
        except Exception:
            pass
        return exito

    # --- ENDPOINTS DEL MENÚ CONTEXTUAL MASIVO ---
    def activar_temporal_ctx(self, tree):
        sel = tree.selection()
        if not sel: return
        self._procesar_lote("Activación Temporal", sel, tree, self._activar_una_temporal)

    def instalar_permanente_ctx(self, tree):
        if not self.es_administrador():
            messagebox.showwarning("Permisos Requeridos", "Se requieren permisos de Administrador para instalaciones permanentes.")
            return
        sel = tree.selection()
        if not sel: return
        self._procesar_lote("Instalación Permanente", sel, tree, self._instalar_una_permanente)

    def desinstalar_sistema_ctx(self, tree):
        if not self.es_administrador():
            messagebox.showwarning("Permisos Requeridos", "Se requieren permisos de Administrador para desinstalar componentes del sistema.")
            return
        sel = tree.selection()
        if not sel: return
        self._procesar_lote("Desinstalación del Sistema", sel, tree, self._desinstalar_una_sistema)

    def actualizar_item_maestro(self, path, nuevo_estado):
        for idx, item in enumerate(self.all_items):
            if item[2] == path:
                self.all_items[idx] = (item[0], nuevo_estado, path)
                break

    def add_to_whitelist(self, tipo, tree):
        sel = tree.selection()
        if not sel: return
        
        añadidos = 0
        for item in sel:
            valores = tree.item(item)['values']
            path = valores[2] if len(valores) > 2 else valores[1]
            if tipo == "archivo": 
                nombre_arch = os.path.basename(path)
                if nombre_arch not in self.whitelist["archivos"]:
                    self.whitelist["archivos"].append(nombre_arch)
                    añadidos += 1
            else: 
                dir_path = os.path.dirname(path)
                if dir_path not in self.whitelist["carpetas"]:
                    self.whitelist["carpetas"].append(dir_path)
                    añadidos += 1
                    
        if añadidos > 0:
            self.guardar_whitelist()
            messagebox.showinfo("Lista Blanca Actualizada", f"Se han protegido {añadidos} elementos correctamente.")

    def cargar_whitelist(self):
        if os.path.exists(self.whitelist_file):
            with open(self.whitelist_file, 'r', encoding='utf-8') as f: 
                return json.load(f)
        return {"archivos": [], "carpetas": []}

    def guardar_whitelist(self):
        with open(self.whitelist_file, 'w', encoding='utf-8') as f: 
            json.dump(self.whitelist, f, indent=4)

    def _mover_a_papelera(self, path):
        nombre_archivo = os.path.basename(path)
        destino = os.path.join(self.papelera, nombre_archivo)
        
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
        if not sel: return

        # Si se quiere soportar eliminación múltiple desde el botón:
        fuentes_protegidas = ("segoe", "arial", "calibri", "tahoma", "verdana", "consola", "times", "marlett")
        rutas_a_borrar = []
        
        for item in sel:
            valores = self.tree.item(item)['values']
            nombre_fuente = str(valores[0]).lower()
            path = valores[2]
            nombre_archivo = os.path.basename(path).lower()

            if any(critica in nombre_fuente for critica in fuentes_protegidas) or any(critica in nombre_archivo for critica in fuentes_protegidas):
                messagebox.showerror(
                    "Acción Bloqueada (Seguridad)", 
                    f"La fuente '{valores[0]}' está marcada como CRÍTICA para el funcionamiento de Windows.\n\n"
                    "Para evitar fallos en la interfaz visual, el gestor ha bloqueado su eliminación masiva."
                )
                return
            rutas_a_borrar.append((item, path))

        if messagebox.askyesno("Confirmar", f"¿Estás seguro de que deseas enviar {len(rutas_a_borrar)} fuente(s) a la papelera?"):
            for item, path in rutas_a_borrar:
                self._mover_a_papelera(path)
                self.tree.delete(item)
                self.all_items = [i for i in self.all_items if i[2] != path]
            messagebox.showinfo("Éxito", f"{len(rutas_a_borrar)} archivo(s) movido(s) a papelera.")

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
            valores = tree.item(sel[0])['values']
            path = valores[2] if len(valores) > 2 else valores[1]
            self.selected_path_var.set(path)
            try:
                img_preview = self.generar_preview(path)
                self.preview_lbl.config(image=img_preview, text="")
                self.preview_lbl.image = img_preview 
            except Exception as e:
                self.preview_lbl.config(image='', text=f"No se pudo cargar la vista previa:\n{e}")
          
    def generar_preview(self, font_path):
        bg_color = self.current_bg_color
        text_color = self.current_text_color
        
        img = Image.new('RGB', (850, 200), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        text = self.custom_text_var.get().strip()
        if not text:
            text = "ABC abc 123 - Tipografía"
            
        try:
            font_size = int(self.font_size_var.get())
            font = ImageFont.truetype(font_path, font_size)
            draw.text((20, 100 - (font_size // 2)), text, fill=text_color, font=font)
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
        # win = self._preparar_modal("Configuración General", 600, 250)
        # win.columnconfigure(1, weight=1)

        # tk.Label(win, text="Ruta de Reportes:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        # entry_reporte = tk.Entry(win)
        # entry_reporte.insert(0, self.ruta_reporte)
        # entry_reporte.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        # tk.Button(win, text="Cambiar...", command=lambda: self.seleccionar_ruta(entry_reporte, True)).grid(row=0, column=2, padx=10, pady=10)

        # tk.Label(win, text="Ruta de Papelera:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        # entry_papelera = tk.Entry(win)
        # entry_papelera.insert(0, self.papelera)
        # entry_papelera.grid(row=1, column=1, padx=5, pady=10, sticky="ew")
        # tk.Button(win, text="Cambiar...", command=lambda: self.seleccionar_ruta(entry_papelera, True)).grid(row=1, column=2, padx=10, pady=10)
        
        win = self._preparar_modal("Configuración General", 600, 250)
        win.columnconfigure(1, weight=1)

        # ... etiquetas y entradas (igual que antes) ...
        tk.Label(win, text="Ruta de Reportes:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        entry_reporte = tk.Entry(win)
        entry_reporte.insert(0, self.ruta_reporte)
        entry_reporte.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        
        # CAMBIO AQUÍ: Llamamos al método nuevo
        tk.Button(win, text="Cambiar...", command=lambda: self.seleccionar_ruta_seguro(win, entry_reporte)).grid(row=0, column=2, padx=10, pady=10)

        tk.Label(win, text="Ruta de Papelera:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        entry_papelera = tk.Entry(win)
        entry_papelera.insert(0, self.papelera)
        entry_papelera.grid(row=1, column=1, padx=5, pady=10, sticky="ew")
        
        # CAMBIO AQUÍ: Llamamos al método nuevo
        tk.Button(win, text="Cambiar...", command=lambda: self.seleccionar_ruta_seguro(win, entry_papelera)).grid(row=1, column=2, padx=10, pady=10)

        btn_frame = tk.Frame(win)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=20)
        
        tk.Button(btn_frame, text="Guardar Cambios", command=lambda: self.guardar_y_cerrar(win, entry_reporte, entry_papelera), bg="#d4edda").pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Cancelar", command=win.destroy).pack(side=tk.LEFT, padx=10)
        

    def guardar_y_cerrar(self, win, entry_rep, entry_pap):
        self.ruta_reporte = entry_rep.get()
        self.papelera = entry_pap.get()
        if not os.path.exists(self.papelera):
            os.makedirs(self.papelera, exist_ok=True)
        self.guardar_configuracion_json()
        messagebox.showinfo("Guardado", "Configuración actualizada.", parent=win)
        win.destroy()

    def seleccionar_ruta(self, entry, es_carpeta=True):
        ruta = filedialog.askdirectory() if es_carpeta else filedialog.asksaveasfilename()
        if ruta:
            entry.delete(0, tk.END)
            entry.insert(0, ruta)   

    def guardar_configuracion_json(self):
        config = {"ruta_reporte": self.ruta_reporte, "papelera": self.papelera}
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
      
     # --------------filtrar_fuentes se modifico para Coleccion   
    def filtrar_fuentes(self):
        query = self.search_var.get().lower()
        filtro_estado = self.filtro_estado_var.get()
        coleccion_activa = self.coleccion_var.get()
        
        # Limpiar tabla
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        for nombre, estado, ruta in self.all_items:
            # Lógica de filtros
            cumple_query = query in nombre.lower()
            cumple_estado = (filtro_estado == "Todas") or (
                (filtro_estado == "Instaladas" and estado == "Instalada") or
                (filtro_estado == "Temporales" and estado == "Temporal") or
                (filtro_estado == "No Instaladas" and estado == "No Instalada")
            )
            # Lógica de colección
            cumple_coleccion = (coleccion_activa == "Todas") or (ruta in self.colecciones.get(coleccion_activa, []))
            
            if cumple_query and cumple_estado and cumple_coleccion:
                tag = "normal"
                if estado == "Instalada": tag = "instalada"
                elif estado == "Temporal": tag = "temporal"
                self.tree.insert("", "end", values=(nombre, estado, ruta), tags=(tag,))
                
    def desactivar_todas_las_temporales(self):
        if not self.fuentes_temporales:
            messagebox.showinfo("Limpiar Memoria", "No hay fuentes temporales cargadas en la memoria para desactivar.")
            return

        cant_fuentes = len(self.fuentes_temporales)
        rutas_a_remover = list(self.fuentes_temporales)
        removidas_con_exito = 0
        
        for path in rutas_a_remover:
            resultado = ctypes.windll.gdi32.RemoveFontResourceW(path)
            if resultado != 0:
                self.fuentes_temporales.discard(path)
                self.actualizar_item_maestro(path, "No Instalada")
                removidas_con_exito += 1

        ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
        self.filtrar_fuentes()
        messagebox.showinfo("Éxito", f"Se han liberado y desactivado {removidas_con_exito} de {cant_fuentes} fuentes de la memoria.")
    
    def cargar_colecciones(self):
        if os.path.exists("colecciones.json"):
            with open("colecciones.json", "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def guardar_colecciones(self):
        with open("colecciones.json", "w", encoding="utf-8") as f:
            json.dump(self.colecciones, f, indent=4)

    def añadir_a_coleccion(self):
        seleccion = self.tree.selection()
        if not seleccion: return
        
        # Pedir nombre de colección
        from tkinter import simpledialog
        nueva_coleccion = simpledialog.askstring("Colección", "Nombre de la colección (o nueva):")
        if not nueva_coleccion: return
        
        if nueva_coleccion not in self.colecciones:
            self.colecciones[nueva_coleccion] = []
            # Actualizar combobox
            self.actualizar_combobox_colecciones()
            
        for item in seleccion:
            ruta = self.tree.item(item, "values")[2]
            if ruta not in self.colecciones[nueva_coleccion]:
                self.colecciones[nueva_coleccion].append(ruta)
        
        self.guardar_colecciones()
        messagebox.showinfo("Éxito", f"Fuentes añadidas a '{nueva_coleccion}'")

    def actualizar_combobox_colecciones(self):
        lista = ["Todas"] + list(self.colecciones.keys())
        self.cb_coleccion['values'] = lista
        
    # -------------------Coleccion---------------------------------------
    
    
    
    def cargar_colecciones(self):
        if os.path.exists("colecciones.json"):
            with open("colecciones.json", "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def guardar_colecciones(self):
        with open("colecciones.json", "w", encoding="utf-8") as f:
            json.dump(self.colecciones, f, indent=4)

    def añadir_a_coleccion(self):
        seleccion = self.tree.selection()
        if not seleccion:
            messagebox.showwarning("Selección", "Por favor, selecciona al menos una fuente.")
            return
        
        # Crear ventana emergente
        win = tk.Toplevel(self.root)
        self.centrar_ventana(win, 300, 200)
        win.title("Añadir a Colección")
        win.geometry("300x150")
        win.grab_set()
        
        tk.Label(win, text="Selecciona o escribe una colección:").pack(pady=10)
        
        # Combobox con colecciones existentes
        colecciones_disponibles = list(self.colecciones.keys())
        cb = ttk.Combobox(win, values=colecciones_disponibles)
        cb.pack(pady=5)
        
        def confirmar():
            nombre = cb.get()
            if not nombre:
                messagebox.showerror("Error", "Debes ingresar un nombre de colección.")
                return
            
            # Si no existe, se crea automáticamente
            if nombre not in self.colecciones:
                self.colecciones[nombre] = []
                self.actualizar_combobox_colecciones()
            
            # Añadir rutas
            for item in seleccion:
                ruta = self.tree.item(item, "values")[2]
                if ruta not in self.colecciones[nombre]:
                    self.colecciones[nombre].append(ruta)
            
            self.guardar_colecciones()
            messagebox.showinfo("Éxito", f"Fuentes añadidas a '{nombre}'")
            win.destroy()
            
        btn = tk.Button(win, text="Aceptar", command=confirmar)
        btn.pack(pady=10)

    def actualizar_combobox_colecciones(self):
        lista = ["Todas"] + list(self.colecciones.keys())
        self.cb_coleccion['values'] = lista
    # ---------------------------------------------------------- 


    # ---------------------------------------------------------- 
    def seleccionar_ruta_seguro(self, win, entry_widget):
        # 1. Liberar el foco modal de la ventana actual
        win.grab_release()
        
        # 2. Abrir el diálogo de selección de carpeta
        nueva_ruta = filedialog.askdirectory(title="Seleccionar Carpeta", parent=win)
        
        # 3. Volver a tomar el foco para mantener la ventana como modal
        win.grab_set()
        
        if nueva_ruta:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, nueva_ruta)

        
if __name__ == "__main__":
    root = tk.Tk()
    app = FontManagerApp(root)
    root.mainloop()