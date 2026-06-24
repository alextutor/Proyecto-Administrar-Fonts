# Implementamos en la parte inferior un boton  Desactivación Rápida de Fuentes Temporales (Limpiar Memoria). (Limpia todas la fuentes temporales que hemos cargado )
# al costado de cancelar scan
# es diferente al hacer click derecho en cada uno de las fuentes 

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
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
        self.root.title("Gestor Profesional de Fuentes - V19.1 (Estados y Acciones)")
        
        # 1. Definir dimensiones deseadas
        ancho = 1250
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
        tk.Button(btn_frame, text="Eliminar Archivo", command=self.delete_item, bg="#ffcccb").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Limpiar Duplicados", command=self.limpiar_duplicados, bg="#ffcccb").pack(side=tk.LEFT, padx=5)
        
        # NUEVO BOTÓN: Limpieza rápida de memoria tipográfica
        tk.Button(btn_frame, text="Desactivar Temporales", command=self.desactivar_todas_las_temporales, bg="#ffe8cc", fg="#d97706", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)
        
        
        self.btn_cancel = tk.Button(btn_frame, text="Cancelar Scan", command=self.stop_scan, bg="#f8d7da", state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(btn_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.lbl_percent = tk.Label(btn_frame, text="0%")
        self.lbl_percent.pack(side=tk.LEFT, padx=5)
    
    def es_administrador(self):
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False

    def obtener_estado_fuente(self, ruta_archivo):
        nombre_base = os.path.basename(ruta_archivo)
        
        # 1. Comprobar si está activada temporalmente en la sesión actual
        if ruta_archivo in self.fuentes_temporales:
            return "Temporal"
            
        # 2. Comprobar si está instalada en el sistema (C:\Windows\Fonts)
        ruta_sistema = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Fonts', nombre_base)
        if os.path.exists(ruta_sistema):
            return "Instalada"
            
        # 3. Comprobar mediante el Registro de Windows por si tiene otro nombre de archivo
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
        
        tree = ttk.Treeview(container, columns=columnas, show='headings', yscrollcommand=scroll.set)
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
        files = [os.path.join(r, f) for r, _, fs in os.walk(ruta) for f in fs if f.lower().endswith(('.ttf', '.otf'))]
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
        
        # Acciones avanzadas de Fuentes de Sistema
        menu.add_command(label="⚡ Activar temporalmente (Memoria)", command=lambda: self.activar_temporal_ctx(tree))
        menu.add_command(label="💾 Instalar permanentemente", command=lambda: self.instalar_permanente_ctx(tree))
        menu.add_command(label="❌ Desinstalar del Sistema", command=lambda: self.desinstalar_sistema_ctx(tree))
        menu.add_separator()
        menu.add_command(label="Proteger Archivo", command=lambda: self.add_to_whitelist("archivo", tree))
        menu.add_command(label="Proteger Carpeta", command=lambda: self.add_to_whitelist("carpeta", tree))
        
        # Evento corregido para identificar sobre cuál item se hace click derecho antes de desplegar
        def post_menu(e):
            item = tree.identify_row(e.y)
            if item:
                tree.selection_set(item)
                menu.post(e.x_root, e.y_root)
                
        tree.bind("<Button-3>", post_menu)

    # --- ACCIONES DE GESTIÓN TIPOGRÁFICA (WINDOWS API) ---
    
    def activar_temporal_ctx(self, tree):
        sel = tree.selection()
        if not sel: return
        valores = tree.item(sel[0])['values']
        # En la tabla principal la ruta está en el índice 2, en duplicados o papelera varía.
        path = valores[2] if len(valores) > 2 else valores[1]
        
        if not os.path.exists(path):
            messagebox.showerror("Error", "El archivo de origen ya no existe.")
            return

        # AddFontResourceW carga la fuente en memoria para la sesión activa
        resultado = ctypes.windll.gdi32.AddFontResourceW(path)
        if resultado != 0:
            # Notificar a las aplicaciones abiertas del cambio de tipografías
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
            self.fuentes_temporales.add(path)
            messagebox.showinfo("Éxito", "Fuente activada temporalmente en memoria.\nSe desactivará al reiniciar el equipo.")
            self.actualizar_item_maestro(path, "Temporal")
            self.filtrar_fuentes()
        else:
            messagebox.showerror("Error", "No se pudo cargar la fuente en memoria.")

    def instalar_permanente_ctx(self, tree):
        if not self.es_administrador():
            messagebox.showwarning("Permisos Requeridos", "Para instalar fuentes de forma permanente deba ejecutar este gestor como Administrador.")
            return
            
        sel = tree.selection()
        if not sel: return
        valores = tree.item(sel[0])['values']
        path = valores[2] if len(valores) > 2 else valores[1]
        nombre_archivo = os.path.basename(path)
        
        ruta_destino = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Fonts', nombre_archivo)
        
        try:
            # 1. Copiar archivo al directorio del sistema
            if not os.path.exists(ruta_destino):
                shutil.copy(path, ruta_destino)
            
            # 2. Registrar en el registro de Windows de manera definitiva
            # Intentamos extraer el nombre real de la fuente
            font_title = os.path.splitext(nombre_archivo)[0] + " (TrueType)"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts", 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, font_title, 0, winreg.REG_SZ, nombre_archivo)
            except Exception as reg_err:
                print(f"Error de Registro: {reg_err}")
            
            # 3. Notificar al sistema global
            ctypes.windll.gdi32.AddFontResourceW(ruta_destino)
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
            
            messagebox.showinfo("Éxito", "Fuente instalada permanentemente en el sistema.")
            self.actualizar_item_maestro(path, "Instalada")
            self.filtrar_fuentes()
            
        except Exception as e:
            messagebox.showerror("Error de Instalación", f"No se pudo completar la instalación fija:\n{e}")

    def desinstalar_sistema_ctx(self, tree):
        if not self.es_administrador():
            messagebox.showwarning("Permisos Requeridos", "Se necesitan permisos de Administrador para desinstalar componentes del sistema.")
            return

        sel = tree.selection()
        if not sel: return
        valores = tree.item(sel[0])['values']
        path = valores[2] if len(valores) > 2 else valores[1]
        nombre_archivo = os.path.basename(path)
        
        # Evaluar remoción temporal primero si existe en memoria
        if path in self.fuentes_temporales:
            ctypes.windll.gdi32.RemoveFontResourceW(path)
            self.fuentes_temporales.discard(path)
            
        ruta_sistema = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Fonts', nombre_archivo)
        
        try:
            # 1. Remover de memoria del sistema
            if os.path.exists(ruta_sistema):
                ctypes.windll.gdi32.RemoveFontResourceW(ruta_sistema)
                
            # 2. Eliminar del Registro
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
                pass # Fin del bucle o registro no existente
                
            # 3. Eliminar archivo físico de Fonts
            if os.path.exists(ruta_sistema):
                os.remove(ruta_sistema)
                
            # 4. Avisar al entorno global Windows
            ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
            
            messagebox.showinfo("Éxito", "La fuente ha sido retirada del sistema por completo.")
            self.actualizar_item_maestro(path, "No Instalada")
            self.filtrar_fuentes()
            
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un inconveniente al desinstalar:\n{e}")

    def actualizar_item_maestro(self, path, nuevo_estado):
        """Busca en la lista maestra y refresca el estado del item seleccionado"""
        for idx, item in enumerate(self.all_items):
            if item[2] == path:
                self.all_items[idx] = (item[0], nuevo_estado, path)
                break

    # -----------------------------------------------------

    def add_to_whitelist(self, tipo, tree):
        sel = tree.selection()
        if not sel: return
        valores = tree.item(sel[0])['values']
        path = valores[2] if len(valores) > 2 else valores[1]
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

        path = self.tree.item(sel[0])['values'][2]
        self._mover_a_papelera(path)
        self.tree.delete(sel[0])
        
        self.all_items = [item for item in self.all_items if item[2] != path]
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
        win = self._preparar_modal("Configuración General", 600, 250)
        win.columnconfigure(1, weight=1)

        tk.Label(win, text="Ruta de Reportes:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        entry_reporte = tk.Entry(win)
        entry_reporte.insert(0, self.ruta_reporte)
        entry_reporte.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        tk.Button(win, text="Cambiar...", command=lambda: self.seleccionar_ruta(entry_reporte, True)).grid(row=0, column=2, padx=10, pady=10)

        tk.Label(win, text="Ruta de Papelera:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        entry_papelera = tk.Entry(win)
        entry_papelera.insert(0, self.papelera)
        entry_papelera.grid(row=1, column=1, padx=5, pady=10, sticky="ew")
        tk.Button(win, text="Cambiar...", command=lambda: self.seleccionar_ruta(entry_papelera, True)).grid(row=1, column=2, padx=10, pady=10)

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
        filtro_estado = self.filtro_estado_var.get()
        
        # 1. Limpiamos totalmente el Treeview visual
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # 2. Reinsertamos solo lo que cumple con el filtro de texto y de estado
        for nombre, estado, ruta in self.all_items:
            # Validar filtro por cuadro de búsqueda (nombre de la fuente)
            cumple_query = not query or query in nombre.lower()
            
            # Validar filtro por el Combobox de Estados (corregido la coincidencia exacta)
            cumple_estado = (
                (filtro_estado == "Todas") or 
                (filtro_estado == "Instaladas" and estado == "Instalada") or
                (filtro_estado == "Temporales" and estado == "Temporal") or
                (filtro_estado == "No Instaladas" and estado == "No Instalada")
            )
            
            if cumple_query and cumple_estado:
                tag = "normal"
                if estado == "Instalada": 
                    tag = "instalada"
                elif estado == "Temporal": 
                    tag = "temporal"
                
                self.tree.insert("", "end", values=(nombre, estado, ruta), tags=(tag,))
                
    def desactivar_todas_las_temporales(self):
        """Remueve de la memoria de Windows todas las fuentes cargadas temporalmente en esta sesión"""
        if not self.fuentes_temporales:
            messagebox.showinfo("Limpiar Memoria", "No hay fuentes temporales cargadas en la memoria para desactivar.")
            return

        cant_fuentes = len(self.fuentes_temporales)
        
        # Copiamos las rutas para poder iterar y limpiar de forma segura
        rutas_a_remover = list(self.fuentes_temporales)
        
        removidas_con_exito = 0
        for path in rutas_a_remover:
            # Remover de la memoria RAM de Windows
            resultado = ctypes.windll.gdi32.RemoveFontResourceW(path)
            if resultado != 0:
                self.fuentes_temporales.discard(path)
                # Cambiar el estado de la fuente en la lista maestra a "No Instalada"
                self.actualizar_item_maestro(path, "No Instalada")
                removidas_con_exito += 1

        # Notificar a todas las ventanas del sistema de forma colectiva
        ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
        
        # Refrescar y filtrar la tabla visual de inmediato
        self.filtrar_fuentes()
        
        messagebox.showinfo("Éxito", f"Se han liberado y desactivado {removidas_con_exito} de {cant_fuentes} fuentes de la memoria.")

        
            
if __name__ == "__main__":
    root = tk.Tk()
    app = FontManagerApp(root)
    root.mainloop()