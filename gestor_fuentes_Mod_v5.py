import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading, os, hashlib, shutil, zipfile
from PIL import Image, ImageDraw, ImageFont, ImageTk

class FontManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Profesional de Fuentes - Auditoría V9")
        self.root.geometry("1200x750")
        
        # Variables de configuración
        self.ruta_reporte = os.getcwd()
        self.is_running = False
        self.papelera = os.path.join(os.getcwd(), "Papelera_Fuentes")
        if not os.path.exists(self.papelera): os.makedirs(self.papelera)
        
        # --- MENÚ DE CONFIGURACIÓN ---
        menubar = tk.Menu(root)
        root.config(menu=menubar)
        config_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Configuración", menu=config_menu)
        config_menu.add_command(label="Establecer carpeta de Reportes", command=self.configurar_reporte)

        # --- UI: Top ---
        top_frame = tk.Frame(root, padx=10, pady=10)
        top_frame.pack(fill=tk.X)
        self.path_entry = tk.Entry(top_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(top_frame, text="Carpeta Fuentes", command=self.browse).pack(side=tk.LEFT)

        # --- UI: Centro ---
        main_frame = tk.Frame(root, padx=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_columnconfigure(0, weight=3)
        main_frame.grid_columnconfigure(1, weight=2)

        table_container = tk.Frame(main_frame)
        table_container.grid(row=0, column=0, sticky="nsew")
        self.tree = ttk.Treeview(table_container, columns=("Nombre", "Estado", "Ruta"), show='headings')
        self.tree.heading("Nombre", text="Fuente / ZIP"); self.tree.heading("Estado", text="Estado")
        self.tree.column("Ruta", width=0, stretch=tk.NO)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.preview)

        self.preview_lbl = tk.Label(main_frame, text="Vista previa", bg="white", relief="sunken")
        self.preview_lbl.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # --- UI: Bottom ---
        btn_frame = tk.Frame(root, pady=10)
        btn_frame.pack(fill=tk.X, padx=10)
        
        tk.Button(btn_frame, text="Analizar", command=self.start_scan, bg="#d4edda").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Eliminar", command=self.delete_item, bg="#ffcccb").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Generar Reporte TXT", command=self.guardar_reporte, bg="#bbdefb").pack(side=tk.LEFT, padx=5)
        self.btn_cancel = tk.Button(btn_frame, text="Cancelar", command=self.stop_scan, bg="#f8d7da", state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(btn_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

    def configurar_reporte(self):
        ruta = filedialog.askdirectory(title="Seleccionar carpeta para reportes")
        if ruta:
            self.ruta_reporte = ruta
            messagebox.showinfo("Configuración", f"Reportes se guardarán en:\n{self.ruta_reporte}")

    def guardar_reporte(self):
        archivo = os.path.join(self.ruta_reporte, "reporte_fuentes.txt")
        try:
            with open(archivo, "w", encoding="utf-8") as f:
                for child in self.tree.get_children():
                    item = self.tree.item(child)
                    f.write(f"{item['values'][0]} | Estado: {item['values'][1]}\n")
            messagebox.showinfo("Éxito", f"Reporte guardado en:\n{archivo}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar: {e}")

    def browse(self):
        d = filedialog.askdirectory()
        if d: self.path_entry.delete(0, tk.END); self.path_entry.insert(0, d)

    def start_scan(self):
        self.is_running = True
        self.btn_cancel.config(state=tk.NORMAL)
        for i in self.tree.get_children(): self.tree.delete(i)
        threading.Thread(target=self.scan_logic, daemon=True).start()

    def scan_logic(self):
        ruta = self.path_entry.get()
        files = [os.path.join(r, f) for r, _, fs in os.walk(ruta) for f in fs if f.lower().endswith(('.ttf', '.otf', '.zip'))]
        for i, f in enumerate(files):
            if not self.is_running: break
            if f.lower().endswith('.zip'):
                with zipfile.ZipFile(f, 'r') as z:
                    for name in z.namelist():
                        if name.lower().endswith(('.ttf', '.otf')):
                            self.root.after(0, lambda n=f"{os.path.basename(f)} -> {name}", p=f: self.tree.insert("", "end", values=(n, "ZIP/CONT", p)))
            else:
                self.root.after(0, lambda n=os.path.basename(f), p=f: self.tree.insert("", "end", values=(n, "OK", p)))
            self.root.after(0, lambda v=((i+1)/len(files))*100: self.progress.config(value=v))
        self.root.after(0, lambda: self.btn_cancel.config(state=tk.DISABLED))

    def delete_item(self):
        sel = self.tree.selection()
        if not sel: return
        path = self.tree.item(sel[0])['values'][2]
        if messagebox.askyesno("Confirmar", "¿Eliminar archivo?"):
            shutil.move(path, os.path.join(self.papelera, os.path.basename(path)))
            self.tree.delete(sel[0])

    def stop_scan(self): self.is_running = False

    def preview(self, e):
        sel = self.tree.selection()
        if not sel: return
        path = self.tree.item(sel[0])['values'][2]
        if path.lower().endswith('.zip'):
            self.preview_lbl.config(text="Es un archivo ZIP (no previsualizable)")
            return
        try:
            img = Image.new('RGB', (500, 200), "white")
            d = ImageDraw.Draw(img)
            d.text((10, 50), "AaBbCc 123", font=ImageFont.truetype(path, 40), fill="black")
            img_tk = ImageTk.PhotoImage(img)
            self.preview_lbl.config(image=img_tk, text="")
            self.preview_lbl.image = img_tk
        except: self.preview_lbl.config(text="Error de renderizado")

if __name__ == "__main__":
    root = tk.Tk()
    FontManagerApp(root)
    root.mainloop()