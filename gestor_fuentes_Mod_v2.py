import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading, os, hashlib, shutil
from PIL import Image, ImageDraw, ImageFont, ImageTk

class FontManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor Profesional de Fuentes - Auditoría V6")
        self.root.geometry("1200x700")
        
        self.is_running = False
        self.papelera = os.path.join(os.getcwd(), "Papelera_Fuentes")
        if not os.path.exists(self.papelera): os.makedirs(self.papelera)
        
        # --- UI: Top ---
        top_frame = tk.Frame(root, padx=10, pady=10)
        top_frame.pack(fill=tk.X)
        self.path_entry = tk.Entry(top_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(top_frame, text="Carpeta", command=self.browse).pack(side=tk.LEFT)

        # --- UI: Centro ---
        main_frame = tk.Frame(root, padx=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_columnconfigure(0, weight=3)
        main_frame.grid_columnconfigure(1, weight=2)

        # Tabla
        table_container = tk.Frame(main_frame)
        table_container.grid(row=0, column=0, sticky="nsew")
        self.tree = ttk.Treeview(table_container, columns=("Nombre", "Estado", "Ruta"), show='headings')
        self.tree.heading("Nombre", text="Fuente"); self.tree.column("Nombre", width=200)
        self.tree.heading("Estado", text="Estado"); self.tree.column("Estado", width=80)
        self.tree.column("Ruta", width=0, stretch=tk.NO)
        
        scrollbar = ttk.Scrollbar(table_container, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.preview)

        # Preview
        self.preview_lbl = tk.Label(main_frame, text="Vista previa", bg="white", relief="sunken")
        self.preview_lbl.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # --- UI: Bottom ---
        btn_frame = tk.Frame(root, pady=10)
        btn_frame.pack(fill=tk.X)
        self.btn_analyze = tk.Button(btn_frame, text="Analizar", command=self.start_scan, bg="#d4edda")
        self.btn_analyze.pack(side=tk.LEFT, padx=5)
        self.btn_cancel = tk.Button(btn_frame, text="Cancelar", command=self.stop_scan, bg="#f8d7da", state=tk.DISABLED)
        self.btn_cancel.pack(side=tk.LEFT, padx=5)
        
        self.progress = ttk.Progressbar(btn_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

    def browse(self):
        d = filedialog.askdirectory()
        if d: self.path_entry.delete(0, tk.END); self.path_entry.insert(0, d)

    def start_scan(self):
        self.is_running = True
        self.btn_analyze.config(state=tk.DISABLED)
        self.btn_cancel.config(state=tk.NORMAL)
        self.progress['value'] = 0
        for i in self.tree.get_children(): self.tree.delete(i)
        threading.Thread(target=self.scan_logic, daemon=True).start()

    def stop_scan(self):
        self.is_running = False
        self.btn_analyze.config(state=tk.NORMAL)
        self.btn_cancel.config(state=tk.DISABLED)

    def scan_logic(self):
        ruta = self.path_entry.get()
        files = [os.path.join(r, f) for r, _, fs in os.walk(ruta) for f in fs if f.lower().endswith(('.ttf', '.otf'))]
        total = len(files)
        
        for i, f in enumerate(files):
            if not self.is_running: break
            # Insertar en tabla
            self.root.after(0, lambda n=os.path.basename(f), p=f: self.tree.insert("", "end", values=(n, "OK", p)))
            # Actualizar barra
            progress_val = ((i + 1) / total) * 100
            self.root.after(0, lambda v=progress_val: self.progress.config(value=v))
        
        self.root.after(0, self.stop_scan)

    def preview(self, e):
        sel = self.tree.selection()
        if not sel: return
        path = self.tree.item(sel[0])['values'][2]
        try:
            img = Image.new('RGB', (500, 200), "white")
            d = ImageDraw.Draw(img)
            d.text((10, 50), "AaBbCc 123", font=ImageFont.truetype(path, 40), fill="black")
            img_tk = ImageTk.PhotoImage(img)
            self.preview_lbl.config(image=img_tk, text="")
            self.preview_lbl.image = img_tk
        except: self.preview_lbl.config(text="Error al renderizar")

if __name__ == "__main__":
    root = tk.Tk()
    FontManagerApp(root)
    root.mainloop()