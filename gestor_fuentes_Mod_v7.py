import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading, os, hashlib, shutil
from PIL import Image, ImageDraw, ImageFont, ImageTk

class FontManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Profesional de Fuentes - Auditoría V14")
        self.root.geometry("1200x900")
        
        self.is_running = False
        self.ruta_reporte = os.getcwd()
        self.papelera = os.path.join(os.getcwd(), "Papelera_Fuentes")
        if not os.path.exists(self.papelera): os.makedirs(self.papelera)
        
        # --- MENÚ ---
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configuración", menu=config_menu)
        config_menu.add_command(label="Establecer carpeta de Reportes", command=self.configurar_reporte)

        # --- TOP ---
        top_frame = tk.Frame(root, padx=10, pady=5)
        top_frame.pack(fill=tk.X)
        self.path_entry = tk.Entry(top_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(top_frame, text="Carpeta Fuentes", command=self.browse).pack(side=tk.LEFT)

        # --- PANELES ---
        paned = tk.PanedWindow(root, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Panel Superior (30% Lista / 70% Preview)
        top_panel = tk.Frame(paned)
        paned.add(top_panel, height=450)
        h_paned = tk.PanedWindow(top_panel, orient=tk.HORIZONTAL)
        h_paned.pack(fill=tk.BOTH, expand=True)

        list_frame = tk.Frame(h_paned)
        h_paned.add(list_frame, width=360)
        self.tree = self.crear_tabla(list_frame, "Fuentes", ["Nombre", "Ruta"])
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_details(self.tree))

        preview_frame = tk.Frame(h_paned)
        h_paned.add(preview_frame, width=840)
        tk.Label(preview_frame, text="Vista Previa", font=("Arial", 10, "bold")).pack(anchor="w")
        self.preview_lbl = tk.Label(preview_frame, text="Selecciona una fuente", bg="white", relief="sunken")
        self.preview_lbl.pack(fill=tk.BOTH, expand=True, pady=5)

        # Panel Inferior (Duplicados)
        bot_panel = tk.Frame(paned)
        paned.add(bot_panel, height=200)
        self.tree_dup = self.crear_tabla(bot_panel, "Duplicados detectados", ["Nombre", "Ruta", "Duplicado de (Original)"])
        self.tree_dup.bind("<<TreeviewSelect>>", lambda e: self.show_details(self.tree_dup))

        # --- FOOTER (RUTA) ---
        path_info_frame = tk.Frame(root, padx=10, pady=5)
        path_info_frame.pack(fill=tk.X)
        tk.Label(path_info_frame, text="Ruta seleccionada:").pack(side=tk.LEFT)
        self.selected_path_var = tk.StringVar()
        tk.Entry(path_info_frame, textvariable=self.selected_path_var, state="readonly").pack(fill=tk.X, padx=5)

        # --- BOTONES ---
        btn_frame = tk.Frame(root, pady=10)
        btn_frame.pack(fill=tk.X, padx=10)
        tk.Button(btn_frame, text="Analizar", command=self.start_scan, bg="#d4edda").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Eliminar Selección", command=self.delete_item, bg="#ffcccb").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Limpiar Duplicados", command=self.limpiar_duplicados, bg="#ffcccb").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Reporte TXT", command=self.guardar_reporte, bg="#bbdefb").pack(side=tk.LEFT, padx=5)
        self.btn_cancel = tk.Button(btn_frame, text="Cancelar", command=self.stop_scan, bg="#f8d7da", state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)
        self.progress = ttk.Progressbar(btn_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

    def crear_tabla(self, parent, titulo, columnas):
        tk.Label(parent, text=titulo, font=("Arial", 10, "bold")).pack(anchor="w")
        container = tk.Frame(parent)
        container.pack(fill=tk.BOTH, expand=True)
        tree = ttk.Treeview(container, columns=columnas, show='headings')
        for col in columnas:
            tree.heading(col, text=col)
        tree.column("Ruta", width=0, stretch=tk.NO)
        scroll = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        return tree

    def show_details(self, tree):
        sel = tree.selection()
        if sel:
            path = tree.item(sel[0])['values'][1]
            self.selected_path_var.set(path)
            if tree == self.tree: self.update_preview(path)

    def update_preview(self, path):
        try:
            img = Image.new('RGB', (800, 300), "white")
            d = ImageDraw.Draw(img)
            d.text((20, 100), "AaBbCc 123", font=ImageFont.truetype(path, 60), fill="black")
            img_tk = ImageTk.PhotoImage(img)
            self.preview_lbl.config(image=img_tk, text="")
            self.preview_lbl.image = img_tk
        except: self.preview_lbl.config(text="No se puede previsualizar")

    def guardar_reporte(self):
        archivo = os.path.join(self.ruta_reporte, "reporte_fuentes.txt")
        with open(archivo, "w", encoding="utf-8") as f:
            for child in self.tree.get_children():
                f.write(f"{self.tree.item(child)['values'][0]} | {self.tree.item(child)['values'][1]}\n")
        messagebox.showinfo("Hecho", f"Reporte guardado en {archivo}")

    def scan_logic(self):
        ruta = self.path_entry.get()
        seen = {}
        files = [os.path.join(r, f) for r, _, fs in os.walk(ruta) for f in fs if f.lower().endswith(('.ttf', '.otf'))]
        for i, f in enumerate(files):
            if not self.is_running: break
            h = self.get_hash(f)
            if h in seen:
                self.root.after(0, lambda n=os.path.basename(f), p=f, o=seen[h]: self.tree_dup.insert("", "end", values=(n, p, o)))
            else: seen[h] = f
            self.root.after(0, lambda n=os.path.basename(f), p=f: self.tree.insert("", "end", values=(n, p)))
            self.root.after(0, lambda v=((i+1)/len(files))*100: self.progress.config(value=v))
        self.root.after(0, lambda: self.btn_cancel.config(state=tk.DISABLED))

    def get_hash(self, path):
        h = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""): h.update(chunk)
        return h.hexdigest()

    def start_scan(self):
        self.is_running = True
        self.btn_cancel.config(state=tk.NORMAL)
        for t in [self.tree, self.tree_dup]:
            for i in t.get_children(): t.delete(i)
        threading.Thread(target=self.scan_logic, daemon=True).start()

    def stop_scan(self): self.is_running = False
    def browse(self):
        d = filedialog.askdirectory()
        if d: self.path_entry.delete(0, tk.END); self.path_entry.insert(0, d)
    def configurar_reporte(self):
        ruta = filedialog.askdirectory()
        if ruta: self.ruta_reporte = ruta
    def delete_item(self):
        sel = self.tree.selection()
        if sel:
            path = self.tree.item(sel[0])['values'][1]
            shutil.move(path, os.path.join(self.papelera, os.path.basename(path)))
            self.tree.delete(sel[0])
    def limpiar_duplicados(self):
        # 1. Obtener todos los items del árbol de duplicados
        items_dup = self.tree_dup.get_children()
        if not items_dup:
            messagebox.showwarning("Aviso", "No hay duplicados para limpiar.")
            return

        if messagebox.askyesno("Confirmar", f"¿Mover {len(items_dup)} archivos a la papelera y actualizar listas?"):
            for item in items_dup:
                path_a_borrar = self.tree_dup.item(item)['values'][1]
                
                # Mover a papelera
                try:
                    if os.path.exists(path_a_borrar):
                        shutil.move(path_a_borrar, os.path.join(self.papelera, os.path.basename(path_a_borrar)))
                    
                    # Eliminar de la lista de duplicados
                    self.tree_dup.delete(item)
                    
                    # 2. Sincronizar: Buscar y eliminar de la lista principal
                    for main_item in self.tree.get_children():
                        if self.tree.item(main_item)['values'][1] == path_a_borrar:
                            self.tree.delete(main_item)
                            break
                except Exception as e:
                    print(f"Error al limpiar {path_a_borrar}: {e}")
            
            messagebox.showinfo("Limpieza", "Duplicados limpiados y listas sincronizadas.")

if __name__ == "__main__":
    root = tk.Tk()
    FontManagerApp(root)
    root.mainloop()