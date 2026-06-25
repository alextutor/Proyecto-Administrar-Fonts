# -*- coding: utf-8 -*-
# 

# 📋 Análisis y Planificación de la Estructura
# Para implementar estas tres grandes mejoras sin saturar la ventana principal ni degradar el rendimiento al renderizar fuentes pesadas, propongo la siguiente estrategia de diseño y lógica de datos:
# 🌟 1. Mapa de Caracteres / Rejilla de Glifos (Grid)
# Diseño e Interfaz: Añadiremos una pestaña o sección colapsable justo debajo o al lado de la vista previa actual. Utilizaremos un contenedor tipo Canvas con un Scrollbar que aloje un entramado dinámico de celdas (Frame o Label).
# Lógica de Datos: Si fontTools está disponible, extraeremos el mapa de caracteres real del archivo (font['cmap'].getBestCmap()). Si no está disponible, usaremos un set estándar de alta compatibilidad por defecto (bloques de caracteres ASCII básicos, acentuados, números y símbolos comunes).
# Interactividad: Cada celda tendrá un evento <Button-1> para ampliar visualmente el glifo en un Tooltip y un evento <Double-Button-1> que copiará automáticamente el carácter al portapapeles (self.root.clipboard_clear() / append()).
# 🌊 2. Cascada de Tamaños Automática
# Diseño e Interfaz: En lugar de renderizar una única etiqueta o imagen de previsualización fija (self.preview_lbl), convertiremos el panel derecho inferior en un contenedor con scroll vertical (ScrollableFrame).
# Lógica de Renderizado: Cuando se seleccione una fuente, el bucle iterará de manera automática sobre un array de tamaños fijos predefinidos: [12pt, 16pt, 24pt, 36pt, 48pt]. Generaremos las sub-imágenes dinámicamente con Pillow (ImageFont.truetype) utilizando el texto actual del buscador y las inyectaremos de golpe en una lista de etiquetas controladas.
# ⚔️ 3. Comparador de Fuentes (Doble Panel)
# Diseño e Interfaz: Crearemos una ventana secundaria modal dedicada a la comparación (self.abrir_ventana_comparador), similar a la lógica que ya implementas con _preparar_modal.
# Estructura Interna: La ventana tendrá una barra superior con un único cuadro de entrada de texto (Entry) sincronizado para ambas muestras. Debajo, un PanedWindow horizontal dividido exactamente al 50/50.
# Mecanismo de Selección: Cada lado del panel tendrá su propio desplegable (Combobox) cargado con la lista de fuentes analizadas disponibles en el maestro (self.all_items). Al cambiar la fuente de cualquier lado, se actualizará instantáneamente su respectivo lienzo (Canvas / Label) de previsualización lado a lado.


import tkinter as tk
from tkinter import filedialog, messagebox, ttk, colorchooser, simpledialog
import threading, os, hashlib, shutil, json, sys
from PIL import Image, ImageDraw, ImageFont, ImageTk
from datetime import datetime
import ctypes
from ctypes import wintypes
import winreg

try:
    from fontTools.ttLib import TTFont
    FONTTOOLS_AVAILABLE = True
except ImportError:
    FONTTOOLS_AVAILABLE = False

WM_FONTCHANGE = 0x001D
HWND_BROADCAST = 0xFFFF

def obtener_nombre_real_fuente(ruta_archivo):
    """
    Lee los metadatos internos de un archivo .ttf o .otf para extraer el nombre completo real.
    """
    if FONTTOOLS_AVAILABLE:
        try:
            font = TTFont(ruta_archivo, fontNumber=0, lazy=True)
            name_table = font['name']
            nombre_completo = None
            
            for record in name_table.names:
                if record.nameID == 4: 
                    if record.isUnicode():
                        nombre_completo = record.string.decode('utf-16-be').strip()
                    else:
                        nombre_completo = record.string.decode('latin-1').strip()
                    break
                    
            if not nombre_completo:
                for record in name_table.names:
                    if record.nameID == 1: 
                        nombre_completo = record.string.decode('utf-16-be' if record.isUnicode() else 'latin-1').strip()
                        break

            font.close()
            if nombre_completo:
                return nombre_completo
        except Exception:
            pass

    try:
        pil_font = ImageFont.truetype(ruta_archivo, 12)
        familia, estilo = pil_font.getname()
        if estilo.lower() == 'regular':
            return familia
        return f"{familia} {estilo}"
    except Exception:
        pass

    return os.path.splitext(os.path.basename(ruta_archivo))[0]


class FontManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Profesional de Fuentes - V21.0 Opti")
        
        ancho = 1420 
        alto = 880
        
        pantalla_ancho = self.root.winfo_screenwidth()
        pantalla_alto = self.root.winfo_screenheight()
        margen_barra_tareas = 100

        x = (pantalla_ancho // 2) - (ancho // 2)
        y = ((pantalla_alto - margen_barra_tareas) // 2) - (alto // 2)    
        
        self.root.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.root.bind("<Escape>", lambda e: self.cerrar_con_confirmacion(e, self.root))
        
        self.is_running = False
        self.whitelist_file = "whitelist.json"
        self.whitelist = self.cargar_whitelist()
        self.fuentes_temporales = set()
    
        self.preview_dark_mode = False  
        self.font_size_var = tk.IntVar(value=32)  
        self.current_bg_color = "#ffffff"
        self.current_text_color = "#000000"
        self.show_details_panel_var = tk.BooleanVar(value=False)
        self.all_items = [] 
    
        self.cargar_configuracion_json()
        if not os.path.exists(self.papelera): 
            os.makedirs(self.papelera)
    
        # --- MENU ---
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configuración", menu=config_menu)
        config_menu.add_command(label="Configuración General", command=self.abrir_ventana_configuracion)
        config_menu.add_command(label="Gestionar Lista Blanca", command=self.abrir_ventana_whitelist)
        config_menu.add_command(label="Gestionar Colecciones (CRUD)", command=self.abrir_ventana_crud_colecciones)
        config_menu.add_command(label="Abrir Papelera", command=self.abrir_ventana_papelera)
        config_menu.add_separator()
        config_menu.add_command(label="Exportar Reporte de Fuentes", command=self.exportar_reporte)
        config_menu.add_command(label="Añadir a Colección", command=self.anadir_a_coleccion)
        
        herramientas_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Herramientas", menu=herramientas_menu)
        herramientas_menu.add_command(label="Comparador de Fuentes (Doble Panel)", command=self.abrir_ventana_comparador)

        ver_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ver", menu=ver_menu)
        ver_menu.add_checkbutton(label="Panel de Información Detallada", variable=self.show_details_panel_var, command=self.toggle_details_panel)

        # --- UI Layout ---
        top_frame = tk.Frame(root, padx=10, pady=5)
        top_frame.pack(fill=tk.X)
        self.path_entry = tk.Entry(top_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        tk.Button(top_frame, text="Carpeta Fuentes", command=self.browse).pack(side=tk.LEFT, padx=2)
        tk.Button(top_frame, text="Fuentes del Sistema", command=self.seleccionar_fuentes_sistema, bg="#e2e8f0").pack(side=tk.LEFT, padx=2)
        
        self.buscar_subcarpetas_var = tk.BooleanVar(value=True)
        self.chk_subcarpetas = tk.Checkbutton(top_frame, text="Incluir subcarpetas", variable=self.buscar_subcarpetas_var)
        self.chk_subcarpetas.pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Analizar", command=self.start_scan, bg="#d4edda").pack(side=tk.LEFT, padx=5)

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
        
        tk.Label(search_frame, text="Colección:").pack(side=tk.LEFT, padx=(10, 5))
        self.coleccion_var = tk.StringVar(value="Todas")
        self.colecciones = self.cargar_colecciones()
        self.cb_coleccion = ttk.Combobox(search_frame, textvariable=self.coleccion_var, values=["Todas"] + list(self.colecciones.keys()), state="readonly", width=15)
        self.cb_coleccion.pack(side=tk.LEFT, padx=2)
        self.cb_coleccion.bind("<<ComboboxSelected>>", lambda e: self.filtrar_fuentes())
        
        self.btn_crud_directo = tk.Button(search_frame, text="...", command=self.abrir_ventana_crud_colecciones, font=("Arial", 9, "bold"), bg="#e2e8f0", width=3, relief="groove")
        self.btn_crud_directo.pack(side=tk.LEFT, padx=(0, 5))
        
        tk.Button(search_frame, text="⚔️ Comparar", command=self.abrir_ventana_comparador, font=("Arial", 9, "bold"), bg="#bfdbfe").pack(side=tk.LEFT, padx=5)

        paned = tk.PanedWindow(root, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        top_panel = tk.Frame(paned)
        paned.add(top_panel, height=430)
        h_paned = tk.PanedWindow(top_panel, orient=tk.HORIZONTAL)
        h_paned.pack(fill=tk.BOTH, expand=True)
        
        list_frame = tk.Frame(h_paned)
        h_paned.add(list_frame, width=520)
        self.tree = self.crear_tabla(list_frame, "Fuentes", ["Nombre", "Estado", "Ruta"], scroll_x=True)
        
        self.tree.tag_configure("instalada", background="#d4edda", foreground="#155724")
        self.tree.tag_configure("temporal", background="#ffe8cc", foreground="#d97706")
        self.tree.tag_configure("normal", background="white", foreground="black")
        
        self.setup_context_menu(self.tree)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_details(self.tree))

        # --- Panel de Vista Previa Enriquecido (Derecha) ---
        preview_frame = tk.Frame(h_paned)
        h_paned.add(preview_frame, width=860)
        
        preview_top_bar = tk.Frame(preview_frame, pady=2)
        preview_top_bar.pack(fill=tk.X, anchor="w")
        
        basic_group = tk.Frame(preview_top_bar)
        basic_group.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        tk.Label(basic_group, text="Texto:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(5, 2))
        self.custom_text_var = tk.StringVar()
        self.custom_text_entry = tk.Entry(basic_group, textvariable=self.custom_text_var, font=("Arial", 10), width=22)
        self.custom_text_entry.pack(side=tk.LEFT, padx=5)
        self.custom_text_entry.bind("<KeyRelease>", lambda e: self.show_details(self.tree))

        self.cb_size = ttk.Combobox(basic_group, textvariable=self.font_size_var, values=[12, 16, 20, 24, 28, 32, 36, 42, 48, 56, 72, 96, 120], state="readonly", width=5)
        self.cb_size.pack(side=tk.LEFT, padx=2)
        self.cb_size.bind("<<ComboboxSelected>>", lambda e: self.show_details(self.tree))

        self.btn_mode = tk.Button(basic_group, text="Modo Claro", command=self.toggle_preview_mode, width=12, bg="#f1f5f9")
        self.btn_mode.pack(side=tk.LEFT, padx=5)

        adv_group = tk.LabelFrame(preview_top_bar, text="Personalización Avanzada", padx=5, pady=2)
        adv_group.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        lbl_a_small = tk.Label(adv_group, text="A", font=("Arial", 8))
        lbl_a_small.pack(side=tk.LEFT, padx=(2, 0))

        self.slider_size = ttk.Scale(adv_group, from_=10, to=150, orient=tk.HORIZONTAL, variable=self.font_size_var, command=lambda e: self.show_details(self.tree))
        self.slider_size.pack(side=tk.LEFT, padx=5)

        lbl_a_large = tk.Label(adv_group, text="A", font=("Arial", 14, "bold"))
        lbl_a_large.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_color_text = tk.Button(adv_group, text="🅰️", font=("Segoe UI Emoji", 10), command=self.choose_text_color, bg="#e2e8f0", width=4)
        self.btn_color_text.pack(side=tk.LEFT, padx=2)
       
        self.btn_color_bg = tk.Button(adv_group, text="🎨", font=("Segoe UI Emoji", 10), command=self.choose_bg_color, bg="#e2e8f0", width=4)
        self.btn_color_bg.pack(side=tk.LEFT, padx=2)

        self.btn_invert = tk.Button(adv_group, text="⇄", font=("Segoe UI Emoji", 10), command=self.invert_colors, bg="#e2e8f0", width=4)
        self.btn_invert.pack(side=tk.LEFT, padx=2)

        self.btn_default = tk.Button(adv_group, text="↺", font=("Segoe UI Emoji", 10), command=self.default_colors, bg="#e2e8f0", width=4)
        self.btn_default.pack(side=tk.LEFT, padx=2)

        # --- Pestañas de Modos de Vista Previa (Normal, Cascada, Glifos) ---
        self.preview_tabs = ttk.Notebook(preview_frame)
        self.preview_tabs.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Pestaña Estándar
        self.tab_normal = tk.Frame(self.preview_tabs)
        self.preview_lbl = tk.Label(self.tab_normal, text="Selecciona una fuente", bg="white", relief="sunken", anchor="w")
        self.preview_lbl.pack(fill=tk.BOTH, expand=True)
        self.preview_tabs.add(self.tab_normal, text="Vista Única")
        
        # Pestaña Cascada
        self.tab_cascada = tk.Frame(self.preview_tabs)
        self.canvas_cascada = tk.Canvas(self.tab_cascada, bg="white")
        self.scroll_cascada = ttk.Scrollbar(self.tab_cascada, orient="vertical", command=self.canvas_cascada.yview)
        self.frame_cascada_inner = tk.Frame(self.canvas_cascada, bg="white")
        self.frame_cascada_inner.bind("<Configure>", lambda e: self.canvas_cascada.configure(scrollregion=self.canvas_cascada.bbox("all")))
        self.canvas_cascada.create_window((0, 0), window=self.frame_cascada_inner, anchor="nw")
        self.canvas_cascada.configure(yscrollcommand=self.scroll_cascada.set)
        self.canvas_cascada.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scroll_cascada.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_tabs.add(self.tab_cascada, text="🌊 Cascada de Tamaños")
        
        # Pestaña Glifos / Mapa de Caracteres
        self.tab_glifos = tk.Frame(self.preview_tabs)
        self.canvas_glifos = tk.Canvas(self.tab_glifos, bg="#f8fafc")
        self.scroll_glifos = ttk.Scrollbar(self.tab_glifos, orient="vertical", command=self.canvas_glifos.yview)
        self.frame_glifos_inner = tk.Frame(self.canvas_glifos, bg="#f8fafc")
        self.frame_glifos_inner.bind("<Configure>", lambda e: self.canvas_glifos.configure(scrollregion=self.canvas_glifos.bbox("all")))
        self.canvas_glifos.create_window((0, 0), window=self.frame_glifos_inner, anchor="nw")
        self.canvas_glifos.configure(yscrollcommand=self.scroll_glifos.set)
        self.canvas_glifos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scroll_glifos.pack(side=tk.RIGHT, fill=tk.Y)
        self.preview_tabs.add(self.tab_glifos, text="🔠 Mapa de Caracteres")
        
        self.preview_tabs.bind("<<NotebookTabChanged>>", lambda e: self.show_details(self.tree))

        # --- Panel de Información Detallada ---
        self.info_panel_frame = tk.LabelFrame(preview_frame, text="Panel de Información Detallada del Archivo", padx=5, pady=5)
        scroll_info = ttk.Scrollbar(self.info_panel_frame, orient="vertical")
        scroll_info.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_info = tk.Text(self.info_panel_frame, wrap=tk.WORD, yscrollcommand=scroll_info.set, height=6, font=("Consolas", 9), bg="#f8fafc", fg="#334155")
        self.txt_info.pack(fill=tk.BOTH, expand=True)
        scroll_info.config(command=self.txt_info.yview)
        self.txt_info.insert(tk.END, "Selecciona una fuente en la lista superior para visualizar sus metadatos detallados.")
        self.txt_info.config(state=tk.DISABLED)

        bot_panel = tk.Frame(paned)
        paned.add(bot_panel, height=180)
        self.tree_dup = self.crear_tabla(bot_panel, "Duplicados detectados", ["Nombre", "Ruta", "Duplicado de"])
        self.setup_context_menu(self.tree_dup)

        path_info_frame = tk.Frame(root, padx=10, pady=5)
        path_info_frame.pack(fill=tk.X)
        tk.Label(path_info_frame, text="Ruta seleccionada:").pack(side=tk.LEFT)
        self.selected_path_var = tk.StringVar()
        tk.Entry(path_info_frame, textvariable=self.selected_path_var, state="readonly").pack(fill=tk.X, padx=5)

        btn_frame = tk.Frame(root, pady=10)
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Analizar", command=self.start_scan, bg="#d4edda").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Eliminar Archivo", command=self.delete_item, bg="#ffcccb").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Limpiar Duplicados", command=self.limpiar_duplicados, bg="#ffcccb").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Desactivar Temporales", command=self.desactivar_todas_las_temporales, bg="#ffe8cc", fg="#d97706", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Exportar Reporte", command=self.exportar_reporte, bg="#ffe8cc", fg="#d97706", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
             
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
            self.btn_mode.config(text="Modo Oscuro", bg="#1e293b", fg="white")
            self.current_bg_color = "#1e293b"
            self.current_text_color = "#ffffff"
        else:
            self.btn_mode.config(text="Modo Claro", bg="#f1f5f9", fg="black")
            self.current_bg_color = "#ffffff"
            self.current_text_color = "#000000"
        self.show_details(self.tree)

    def toggle_details_panel(self):
        if self.show_details_panel_var.get():
            self.info_panel_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            self.show_details(self.tree)
        else:
            self.info_panel_frame.pack_forget()

    def seleccionar_fuentes_sistema(self):
        ruta_sistema = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Fonts', '')
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
        
    def crear_tabla(self, parent, titulo, columnas, scroll_x=False):
        tk.Label(parent, text=titulo, font=("Arial", 10, "bold")).pack(anchor="w")
        container = tk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)
        
        scroll_y = ttk.Scrollbar(container, orient="vertical")
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        if scroll_x:
            scroll_h = ttk.Scrollbar(container, orient="horizontal")
            scroll_h.pack(side=tk.BOTTOM, fill=tk.X)
            tree = ttk.Treeview(container, columns=columnas, show='headings', 
                                yscrollcommand=scroll_y.set, xscrollcommand=scroll_h.set, selectmode="extended")
            scroll_h.config(command=tree.xview)
        else:
            tree = ttk.Treeview(container, columns=columnas, show='headings', yscrollcommand=scroll_y.set, selectmode="extended")
            
        scroll_y.config(command=tree.yview)
        
        for col in columnas: 
            tree.heading(col, text=col)
        if "Ruta" in columnas:
            tree.column("Ruta", width=250, stretch=tk.YES)
        if "Estado" in columnas:
            tree.column("Estado", width=100, anchor="center")
        if "Nombre" in columnas:
            tree.column("Nombre", width=180, stretch=tk.YES)
            
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
            nombre_b = obtener_nombre_real_fuente(f)
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
        menu.add_command(label="Activar temporalmente (Masivo)", command=lambda: self.activar_temporal_ctx(tree))
        menu.add_command(label="Instalar permanentemente (Masivo)", command=lambda: self.instalar_permanente_ctx(tree))
        menu.add_command(label="Desinstalar del Sistema (Masivo)", command=lambda: self.desinstalar_sistema_ctx(tree))
        menu.add_separator()
        menu.add_command(label="Proteger Archivo(s)", command=lambda: self.add_to_whitelist("archivo", tree))
        menu.add_command(label="Proteger Carpeta(s)", command=lambda: self.add_to_whitelist("carpeta", tree))
        menu.add_command(label="Añadir a Colección", command=self.anadir_a_coleccion)
        
        def post_menu(e):
            item = tree.identify_row(e.y)
            if item:
                if item not in tree.selection():
                    tree.selection_set(item)
                menu.post(e.x_root, e.y_root)
                
        tree.bind("<Button-3>", post_menu)
        
    def _procesar_lote(self, accion_nombre, seleccion, tree, func_accion):
        total = len(seleccion)
        if total == 0: return
        
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
        
        if exitos > 0:
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
            self.filtrar_fuentes()
            
        win.destroy()
        messagebox.showinfo("Operación por Lotes Finalizada", f"{accion_nombre} completada.\n\nÉxitos: {exitos}\nErrores u omitidos: {errores}")

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
        
        anados = 0
        for item in sel:
            valores = tree.item(item)['values']
            path = valores[2] if len(valores) > 2 else valores[1]
            if tipo == "archivo": 
                nombre_arch = os.path.basename(path)
                if nombre_arch not in self.whitelist["archivos"]:
                    self.whitelist["archivos"].append(nombre_arch)
                    anados += 1
            else: 
                dir_path = os.path.dirname(path)
                if dir_path not in self.whitelist["carpetas"]:
                    self.whitelist["carpetas"].append(dir_path)
                    anados += 1
                    
        if anados > 0:
            self.guardar_whitelist()
            messagebox.showinfo("Lista Blanca Actualizada", f"Se han protegido {anados} elementos correctamente.")

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

    def obtener_metadatos_fuente(self, path):
        if not os.path.exists(path):
            return "Archivo físico no encontrado en disco."
            
        tam_bytes = os.path.getsize(path)
        tam_kb = tam_bytes / 1024
        peso_formateado = f"{tam_kb:.2f} KB" if tam_kb < 1024 else f"{(tam_kb/1024):.2f} MB"
        
        ext = os.path.splitext(path)[1].upper()
        fecha_descubierto = datetime.fromtimestamp(os.path.getctime(path)).strftime("%Y-%m-%d %H:%M:%S")
        fecha_modificado = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
        
        info_str = (
            f"📋 ESPECIFICACIONES DEL ARCHIVO:\n"
            f"   🔸 Formato de archivo : {ext}\n"
            f"   🔸 Peso en disco      : {peso_formateado} ({tam_bytes:,} bytes)\n"
            f"   🔸 Descubierto/Creado : {fecha_descubierto}\n"
            f"   🔸 Última modificación: {fecha_modificado}\n\n"
        )
        
        copyright_text = "No disponible"
        version_text = "No disponible"
        nombre_completo = "No disponible"
        disenador_text = "No disponible"
        
        if FONTTOOLS_AVAILABLE:
            try:
                font = TTFont(path, lazy=True)
                name_table = font['name']
                for record in name_table.names:
                    try:
                        string = record.toUnicode()
                    except Exception:
                        continue
                    if record.nameID == 0:
                        copyright_text = string.replace('\n', ' ')
                    elif record.nameID == 4:
                        nombre_completo = string
                    elif record.nameID == 5:
                        version_text = string
                    elif record.nameID == 9:
                        disenador_text = string
                font.close()
            except Exception as e:
                info_str += f"⚠️ No se pudieron extraer los metadatos binarios: {e}\n"
        else:
            try:
                pil_font = ImageFont.truetype(path, 12)
                familia, estilo = pil_font.getname()
                nombre_completo = f"{familia} {estilo}"
            except Exception:
                pass
            info_str += "⚠️ Nota: Instala fontTools ('pip install fonttools') para leer Copyright y Versiones internas.\n\n"
            
        info_str += (
            f"⚙️ PROPIEDADES INTERNAS DE LA TIPOGRAFÍA:\n"
            f"   🔸 Nombre comercial   : {nombre_completo}\n"
            f"   🔸 Versión tipográfica: {version_text}\n"
            f"   🔸 Diseñador/Creador  : {disenador_text}\n"
            f"   🔸 Copyright legal    : {copyright_text}\n"
        )
        return info_str

    def show_details(self, tree):
        sel = tree.selection()
        if not sel:
            return
            
        valores = tree.item(sel[0])['values']
        path = valores[2] if len(valores) > 2 else valores[1]
        self.selected_path_var.set(path)
        
        tab_actual = self.preview_tabs.index(self.preview_tabs.select())
        
        # 1. RENDERIZADO PESTAÑA VISTA ÚNICA
        if tab_actual == 0:
            try:
                img_preview = self.generar_preview(path, int(self.font_size_var.get()), 950, 200)
                self.preview_lbl.config(image=img_preview, text="")
                self.preview_lbl.image = img_preview 
            except Exception as e:
                self.preview_lbl.config(image='', text=f"No se pudo cargar la vista previa:\n{e}")
                
        # 2. RENDERIZADO PESTAÑA CASCADA
        elif tab_actual == 1:
            for widget in self.frame_cascada_inner.winfo_children():
                widget.destroy()
            
            tamanos = [12, 16, 24, 36, 48, 72]
            for sz in tamanos:
                lbl_sz = tk.Label(self.frame_cascada_inner, text=f"{sz} pt", font=("Arial", 8), bg="white", fg="#64748b", anchor="w")
                lbl_sz.pack(fill=tk.X, padx=10, pady=(5, 0))
                
                img_cascada = self.generar_preview(path, sz, 930, sz + 30)
                lbl_img = tk.Label(self.frame_cascada_inner, image=img_cascada, bg="white")
                lbl_img.image = img_cascada
                lbl_img.pack(fill=tk.X, padx=10, pady=(0, 5))
                
        # 3. RENDERIZADO PESTAÑA GLIFOS / MAPA DE CARACTERES
        elif tab_actual == 2:
            for widget in self.frame_glifos_inner.winfo_children():
                widget.destroy()
                
            glifos = []
            if FONTTOOLS_AVAILABLE:
                try:
                    font = TTFont(path, lazy=True)
                    cmap = font['cmap'].getBestCmap()
                    if cmap:
                        glifos = [chr(code) for code in sorted(cmap.keys()) if code > 32]
                    font.close()
                except Exception:
                    pass
            
            if not glifos:
                glifos = [chr(i) for i in range(33, 127)] + [chr(i) for i in range(161, 255)]
                
            cols = 16
            for idx, char in enumerate(glifos):
                row = idx // cols
                col = idx % cols
                
                btn_g = tk.Label(self.frame_glifos_inner, text=char, width=3, height=1, relief="groove", 
                                 bg=self.current_bg_color, fg=self.current_text_color, font=("Arial", 14))
                btn_g.grid(row=row, column=col, padx=2, pady=2)
                
                # Doble clic copia el glifo al portapapeles
                btn_g.bind("<Double-Button-1>", lambda e, c=char: self._copiar_glifo_portapapeles(c))
                
        if self.show_details_panel_var.get():
            meta_datos = self.obtener_metadatos_fuente(path)
            self.txt_info.config(state=tk.NORMAL)
            self.txt_info.delete("1.0", tk.END)
            self.txt_info.insert(tk.END, meta_datos)
            self.txt_info.config(state=tk.DISABLED)
          
    def _copiar_glifo_portapapeles(self, caracter):
        self.root.clipboard_clear()
        self.root.clipboard_append(caracter)
        messagebox.showinfo("Copiado", f"Carácter '{caracter}' copiado al portapapeles.")

    def generar_preview(self, font_path, size, width=950, height=200):
        bg_color = self.current_bg_color
        text_color = self.current_text_color
        
        img = Image.new('RGB', (width, height), color=bg_color)
        draw = ImageDraw.Draw(img)
        
        text = self.custom_text_var.get().strip()
        if not text:
            text = "ABC abc 123 - Tipografía"
            
        try:
            font = ImageFont.truetype(font_path, size)
            draw.text((25, (height // 2) - (size // 2)), text, fill=text_color, font=font)
        except Exception:
            font_default = ImageFont.load_default()
            draw.text((25, height // 2), "Vista previa no disponible", fill=(255, 0, 0), font=font_default)
            
        return ImageTk.PhotoImage(img)
       
    def stop_scan(self): 
        self.is_running = False
        
    def browse(self):
        d = filedialog.askdirectory()
        if d: 
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, d)
   
   
   #----------------Inicio Formulario Comparar --------------------------
    def abrir_ventana_comparador(self):
        """ Abre el panel doble avanzado para comparar dos fuentes lado a lado """
        if not self.all_items:
            messagebox.showwarning("Atención", "Primero debes realizar un análisis para poblar la lista de fuentes.")
            return

        win = self._preparar_modal("⚔️ Comparador de Fuentes en Doble Panel", 1100, 600)
        
        # Barra de Control Superior (Corregido px=10 por padx=10)
        top_ctrl = tk.Frame(win, pady=5, padx=10)
        top_ctrl.pack(fill=tk.X)
        
        tk.Label(top_ctrl, text="Texto de Muestra:").pack(side=tk.LEFT, padx=5)
        txt_muestra_var = tk.StringVar(value="Texto de prueba comparativo - ABC 123")
        entry_muestra = tk.Entry(top_ctrl, textvariable=txt_muestra_var, font=("Arial", 11), width=45)
        entry_muestra.pack(side=tk.LEFT, padx=5)
        
        tk.Label(top_ctrl, text="Tamaño:").pack(side=tk.LEFT, padx=(15, 5))
        size_comp_var = tk.IntVar(value=36)
        cb_size_comp = ttk.Combobox(top_ctrl, textvariable=size_comp_var, values=[16, 24, 32, 36, 42, 48, 64], width=5, state="readonly")
        cb_size_comp.pack(side=tk.LEFT, padx=5)

        # Panel Dividido Principal
        paned_comp = tk.PanedWindow(win, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        paned_comp.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # LADO IZQUIERDO
        frame_izq = tk.Frame(paned_comp, relief="sunken", bd=1)
        paned_comp.add(frame_izq, width=540)
        
        ctrl_izq = tk.Frame(frame_izq, pady=3)
        ctrl_izq.pack(fill=tk.X)
        tk.Label(ctrl_izq, text="Fuente A:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        lista_nombres = [item[0] for item in self.all_items]
        self.cb_font_a = ttk.Combobox(ctrl_izq, values=lista_nombres, state="readonly", width=45)
        self.cb_font_a.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.cb_font_a.current(0)
        
        lbl_preview_a = tk.Label(frame_izq, bg="white", text="Muestra A")
        lbl_preview_a.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)

        # LADO DERECHO
        frame_der = tk.Frame(paned_comp, relief="sunken", bd=1)
        paned_comp.add(frame_der, width=540)
        
        ctrl_der = tk.Frame(frame_der, pady=3)
        ctrl_der.pack(fill=tk.X)
        tk.Label(ctrl_der, text="Fuente B:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        self.cb_font_b = ttk.Combobox(ctrl_der, values=lista_nombres, state="readonly", width=45)
        self.cb_font_b.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.cb_font_b.current(min(1, len(lista_nombres)-1))
        
        lbl_preview_b = tk.Label(frame_der, bg="white", text="Muestra B")
        lbl_preview_b.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        def actualizar_ambas_vistas(*args):
            txt = txt_muestra_var.get()
            sz = size_comp_var.get()
            
            # Procesar Izquierda
            idx_a = self.cb_font_a.current()
            if idx_a >= 0:
                p_a = self.all_items[idx_a][2]
                img_a = self._generar_preview_especifico(p_a, txt, sz, 530, 450)
                lbl_preview_a.config(image=img_a, text="")
                lbl_preview_a.image = img_a
                
            # Procesar Derecha
            idx_b = self.cb_font_b.current()
            if idx_b >= 0:
                p_b = self.all_items[idx_b][2]
                img_b = self._generar_preview_especifico(p_b, txt, sz, 530, 450)
                lbl_preview_b.config(image=img_b, text="")
                lbl_preview_b.image = img_b

        self.cb_font_a.bind("<<ComboboxSelected>>", actualizar_ambas_vistas)
        self.cb_font_b.bind("<<ComboboxSelected>>", actualizar_ambas_vistas)
        cb_size_comp.bind("<<ComboboxSelected>>", actualizar_ambas_vistas)
        entry_muestra.bind("<KeyRelease>", actualizar_ambas_vistas)
        
        actualizar_ambas_vistas()
    #----------------Fin Formulario Comparar --------------------------
    
    
    def _generar_preview_especifico(self, path, texto, size, w, h):
        img = Image.new('RGB', (w, h), color=self.current_bg_color)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(path, size)
            draw.text((20, (h // 2) - (size // 2)), texto, fill=self.current_text_color, font=font)
        except Exception:
            pass
        return ImageTk.PhotoImage(img)

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

    def exportar_reporte(self):
        if not self.all_items:
            messagebox.showwarning("Atención", "No hay datos para exportar. Por favor, realice un análisis analizando una carpeta primero.")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Guardar Reporte de Fuentes Analizadas",
            defaultextension=".csv",
            filetypes=[("Archivo CSV (*.csv)", "*.csv"), ("Reporte HTML (*.html)", "*.html"), ("Documento de Texto (*.txt)", "*.txt")]
        )
        if not file_path: return
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
                    f.write(f"<html><body><h1>Reporte de Fuentes</h1><p>Generado: {ahora_str}</p><table border='1'>")
                    for nombre, estado, ruta in self.all_items:
                        f.write(f"<tr><td>{nombre}</td><td>{estado}</td><td>{ruta}</td></tr>")
                    f.write("</table></body></html>")
            else:
                with open(file_path, mode='w', encoding='utf-8') as f:
                    for nombre, estado, ruta in self.all_items:
                        f.write(f"{nombre} | {estado} | {ruta}\n")
            messagebox.showinfo("Éxito", f"Reporte guardado en:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

    def abrir_ventana_papelera(self):
        win = self._preparar_modal("Gestor de Papelera", 750, 450)
        cols = ("Nombre", "Ruta Original")
        tree = ttk.Treeview(win, columns=cols, show='headings')
        for col in cols: tree.heading(col, text=col)
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        if os.path.exists(self.papelera):
            for f in os.listdir(self.papelera):
                if f.endswith(".json"):
                    try:
                        with open(os.path.join(self.papelera, f), 'r', encoding='utf-8') as j:
                            meta = json.load(j)
                            tree.insert("", "end", values=(meta.get("nombre", f[:-5]), meta.get("ruta_original", "N/A")))
                    except Exception: pass

        def restaurar_seleccion():
            sel = tree.selection()
            if not sel: return
            item = tree.item(sel[0])['values']
            nombre, ruta_origen = item[0], item[1]
            archivo_papelera = os.path.join(self.papelera, nombre)
            if os.path.exists(archivo_papelera):
                os.makedirs(os.path.dirname(ruta_origen), exist_ok=True)
                shutil.move(archivo_papelera, ruta_origen)
                if os.path.exists(archivo_papelera + ".json"): os.remove(archivo_papelera + ".json")
                tree.delete(sel[0])
                messagebox.showinfo("Restaurado", "Elemento devuelto a su origen.", parent=win)
        tk.Button(win, text="Restaurar Selección", command=restaurar_seleccion, bg="#d4edda").pack(pady=10)
        
    def abrir_ventana_configuracion(self):
        win = self._preparar_modal("Configuración General", 600, 250)
        tk.Label(win, text="Ruta de Papelera:").grid(row=0, column=0, padx=10, pady=10)
        entry_papelera = tk.Entry(win, width=40)
        entry_papelera.insert(0, self.papelera)
        entry_papelera.grid(row=0, column=1, padx=5, pady=10)
        
        def guardar():
            self.papelera = entry_papelera.get()
            self.guardar_configuracion_json()
            win.destroy()
        tk.Button(win, text="Guardar", command=guardar, bg="#d4edda").grid(row=1, column=0, columnspan=2, pady=10)

    def guardar_configuracion_json(self):
        with open("config.json", "w", encoding='utf-8') as f:
            json.dump({"ruta_reporte": self.ruta_reporte, "papelera": self.papelera}, f, indent=4)

    def cargar_configuracion_json(self):
        self.ruta_reporte = os.getcwd()
        self.papelera = os.path.join(os.getcwd(), "Papelera_Fuentes")
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r", encoding='utf-8') as f:
                    c = json.load(f)
                    self.ruta_reporte = c.get("ruta_reporte", self.ruta_reporte)
                    self.papelera = c.get("papelera", self.papelera)
            except Exception: pass
      
    def filtrar_fuentes(self):
        query = self.search_var.get().lower()
        filtro_estado = self.filtro_estado_var.get()
        coleccion_activa = self.coleccion_var.get()
        
        for i in self.tree.get_children(): self.tree.delete(i)
            
        for nombre, estado, ruta in self.all_items:
            if query in nombre.lower():
                cumple_estado = (filtro_estado == "Todas") or (filtro_estado[:-1] in estado)
                cumple_col = (coleccion_activa == "Todas") or (ruta in self.colecciones.get(coleccion_activa, []))
                if cumple_estado and cumple_col:
                    tag = "instalada" if estado == "Instalada" else ("temporal" if estado == "Temporal" else "normal")
                    self.tree.insert("", "end", values=(nombre, estado, ruta), tags=(tag,))
                
    def desactivar_todas_las_temporales(self):
        if not self.fuentes_temporales: return
        for path in list(self.fuentes_temporales):
            if ctypes.windll.gdi32.RemoveFontResourceW(path) != 0:
                self.fuentes_temporales.discard(path)
                self.actualizar_item_maestro(path, "No Instalada")
        ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
        self.filtrar_fuentes()
    
    def cargar_colecciones(self):
        if os.path.exists("colecciones.json"):
            with open("colecciones.json", "r", encoding="utf-8") as f: return json.load(f)
        return {}

    def guardar_colecciones(self):
        with open("colecciones.json", "w", encoding="utf-8") as f: json.dump(self.colecciones, f, indent=4)

    def anadir_a_coleccion(self):
        seleccion = self.tree.selection()
        if not seleccion: return
        win = self._preparar_modal("Añadir a Colección", 320, 180)
        cb = ttk.Combobox(win, values=list(self.colecciones.keys()))
        cb.pack(pady=20)
        def conf():
            n = cb.get().strip()
            if n:
                if n not in self.colecciones: self.colecciones[n] = []
                for i in seleccion:
                    r = self.tree.item(i, "values")[2]
                    if r not in self.colecciones[n]: self.colecciones[n].append(r)
                self.guardar_colecciones()
                self.actualizar_combobox_colecciones()
                win.destroy()
        tk.Button(win, text="Aceptar", command=conf, bg="#d4edda").pack()

    def actualizar_combobox_colecciones(self):
        self.cb_coleccion['values'] = ["Todas"] + list(self.colecciones.keys())

    def abrir_ventana_crud_colecciones(self):
        win = self._preparar_modal("Gestión de Colecciones", 800, 500)
        main_paned = tk.PanedWindow(win, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_frame = tk.Frame(main_paned)
        main_paned.add(left_frame, width=280)
        lb_colecciones = tk.Listbox(left_frame, font=("Arial", 10))
        lb_colecciones.pack(fill=tk.BOTH, expand=True)
        
        right_frame = tk.Frame(main_paned)
        main_paned.add(right_frame, width=500)
        tree_fuentes = self.crear_tabla(right_frame, "Fuentes de la Colección", ["Nombre", "Ubicación"])
        
        def ref():
            lb_colecciones.delete(0, tk.END)
            for k in sorted(self.colecciones.keys()): lb_colecciones.insert(tk.END, k)
        ref()
        
        lb_colecciones.bind("<<ListboxSelect>>", lambda e: [
            tree_fuentes.delete(*tree_fuentes.get_children()),
            [tree_fuentes.insert("", "end", values=(os.path.basename(r), r)) for r in self.colecciones.get(lb_colecciones.get(lb_colecciones.curselection()[0]), [])] if lb_colecciones.curselection() else None
        ])
        
        def nueva():
            n = simpledialog.askstring("Nueva", "Nombre:", parent=win)
            if n and n.strip() not in self.colecciones:
                self.colecciones[n.strip()] = []
                self.guardar_colecciones()
                self.actualizar_combobox_colecciones()
                ref()
        tk.Button(left_frame, text="Nueva", command=nueva, bg="#d4edda").pack(side=tk.LEFT)


if __name__ == "__main__":
    root = tk.Tk()
    app = FontManagerApp(root)
    root.mainloop()