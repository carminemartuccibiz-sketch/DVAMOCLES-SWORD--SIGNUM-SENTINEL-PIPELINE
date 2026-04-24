import os, json, gc, tkinter as tk, customtkinter as ctk, psutil
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path

# --- TENTATIVO IMPORTAZIONE MODULI CORE ---
try:
    from core.import_assistant import AdvancedImporter
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False

# --- GESTIONE HARDWARE TELEMETRY ---
try: import GPUtil
except: GPUtil = None

# --- GESTIONE DRAG & DROP (LA CHIAVE DEL FIX) ---
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

# --- DEFINIZIONE CLASSE CON EREDITARIETÀ INCROCIATA ---
# Se DnD è disponibile, ereditiamo da entrambi, altrimenti solo da CTk
if HAS_DND:
    class BaseGUI(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    class BaseGUI(ctk.CTk):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)

class SignumSentinelGUI(BaseGUI):
    def __init__(self):
        super().__init__() # Inizializza entrambi i genitori (Tkinter + DnD)

        self.title("DVAMOCLES SWORD™ | MASTER DATA FORGE")
        self.geometry("1800x950")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Inizializzazione Backend
        self.importer = AdvancedImporter(Path.cwd()) if HAS_BACKEND else None
        
        # Stato dell'applicazione
        self.staged_groups = {} 
        self.project_materials = self.importer.load_existing_vault() if self.importer else {}
        self.tree_state = self._load_state()
        self.active_selection = {"type": None, "id": None}
        self.drop_targets_geometry = []

        # Setup Interfaccia
        self.setup_telemetry_bar()
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, pady=5)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(1, weight=2)
        self.main_container.grid_columnconfigure(2, weight=1)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.setup_staging_panel()
        self.setup_builder_panel()
        self.setup_inspector_panel()
        
        self.update_telemetry()
        
        # Protocollo di chiusura sicura (Liberazione VRAM)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _load_state(self):
        p = Path("config/gui_state.json")
        if p.exists():
            try:
                with open(p, "r") as f: return json.load(f)
            except: pass
        return {}

    def on_closing(self):
        """Spegne l'IA e libera la VRAM prima di uscire."""
        if messagebox.askokcancel("Esci", "Vuoi chiudere e liberare la VRAM?"):
            if self.importer:
                self.importer.unload_ai()
            # Salva lo stato delle cartelle dell'albero
            os.makedirs("config", exist_ok=True)
            with open("config/gui_state.json", "w") as f: 
                json.dump(self.tree_state, f)
            self.destroy()

    def setup_telemetry_bar(self):
        self.telemetry_frame = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#0a0a0a")
        self.telemetry_frame.pack(fill="x", side="top")
        
        self.lbl_cpu = ctk.CTkLabel(self.telemetry_frame, text="CPU: 0% | RAM: 0%", font=("Courier", 12))
        self.lbl_cpu.pack(side="left", padx=20)
        
        # Tasto IA ON/OFF
        self.ai_btn = ctk.CTkButton(self.telemetry_frame, text="IA: OFF", width=60, 
                                     fg_color="#333", command=self.toggle_ai)
        self.ai_btn.pack(side="right", padx=10)

    def toggle_ai(self):
        if not self.importer: return
        if self.importer.ai_model is None:
            self.importer.load_ai()
            self.ai_btn.configure(text="IA: ON", fg_color="#6200ea")
        else:
            self.importer.unload_ai()
            self.ai_btn.configure(text="IA: OFF", fg_color="#333")

    def update_telemetry(self):
        self.lbl_cpu.configure(text=f"CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%")
        self.after(2000, self.update_telemetry)

    # --- PANELS ---
    def setup_staging_panel(self):
        self.staging_frame = ctk.CTkFrame(self.main_container, fg_color="#121212")
        self.staging_frame.grid(row=0, column=0, sticky="nsew", padx=2)
        
        hdr = ctk.CTkFrame(self.staging_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=10)
        ctk.CTkLabel(hdr, text="1. ASSET BROWSER", font=("Arial", 14, "bold")).pack(side="left", padx=10)
        
        ctk.CTkButton(hdr, text="+ Folder", width=80, command=self.browse_folder).pack(side="right", padx=5)

        self.sort_container = ctk.CTkFrame(self.staging_frame, fg_color="transparent")
        self.sort_container.pack(fill="x", padx=10)
        self.auto_sort_btn = ctk.CTkButton(self.sort_container, text="✨ AI AUTO-SORT", fg_color="#6200ea", command=self.execute_auto_sort)
        
        self.stage_scroll = ctk.CTkScrollableFrame(self.staging_frame, fg_color="#1e1e1e")
        self.stage_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Registrazione Drag & Drop (ORA FUNZIONERÀ)
        if HAS_DND:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind('<<Drop>>', self.on_drop)
            except Exception as e:
                print(f"Errore registrazione DnD: {e}")

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder: self._process_paths([folder])

    def on_drop(self, event):
        import re
        # Pulisce i percorsi raggruppati da Windows (quelli con le parentesi graffe)
        paths = [p.strip('{}') for p in re.findall(r'\{.*?\}|\S+', event.data)]
        self._process_paths(paths)

    def _process_paths(self, paths):
        valid_ext = {'.png', '.jpg', '.jpeg', '.tif', '.exr', '.tga', '.mtlx'}
        for p_str in paths:
            p = Path(p_str)
            if p.is_dir():
                files = [str(f) for f in p.rglob("*") if f.suffix.lower() in valid_ext]
                if files:
                    group_name = p.name
                    self.staged_groups[group_name] = [self.importer.auto_detect_file(f) for f in files]
            elif p.suffix.lower() in valid_ext:
                if "Loose_Files" not in self.staged_groups: self.staged_groups["Loose_Files"] = []
                self.staged_groups["Loose_Files"].append(self.importer.auto_detect_file(str(p)))
        
        if self.staged_groups:
            self.auto_sort_btn.pack(fill="x", pady=5)
        self.refresh_staging_ui()

    def refresh_staging_ui(self):
        for w in self.stage_scroll.winfo_children(): w.destroy()
        for group, files in self.staged_groups.items():
            g_frame = ctk.CTkFrame(self.stage_scroll, fg_color="#2c2c2c")
            g_frame.pack(fill="x", pady=2, padx=2)
            ctk.CTkLabel(g_frame, text=f"📁 {group}", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)
            for f in files:
                f_frame = ctk.CTkFrame(g_frame, fg_color="#1a1a1a")
                f_frame.pack(fill="x", pady=1, padx=5)
                # Visualizziamo tipo mappa e risoluzione trovata dall'analizzatore
                meta = f"[{f.get('map_type')} | {f.get('tech_res')}]"
                ctk.CTkLabel(f_frame, text=f"📄 {f['name']} {meta}", font=("Arial", 11)).pack(side="left", padx=5)

    def execute_auto_sort(self):
        for group, files in self.staged_groups.items():
            if group not in self.project_materials:
                self.project_materials[group] = {"provider": "Auto", "folders": {"Root": {"files": files}}}
            else:
                self.project_materials[group]["folders"]["Root"]["files"].extend(files)
        self.staged_groups = {}
        self.auto_sort_btn.pack_forget()
        self.refresh_builder_ui()
        self.refresh_staging_ui()

    def setup_builder_panel(self):
        self.builder_frame = ctk.CTkFrame(self.main_container, fg_color="#161b22")
        self.builder_frame.grid(row=0, column=1, sticky="nsew", padx=2)
        ctk.CTkLabel(self.builder_frame, text="2. PROJECT VAULT", font=("Arial", 14, "bold")).pack(pady=10)
        self.builder_scroll = ctk.CTkScrollableFrame(self.builder_frame, fg_color="#0d1117")
        self.builder_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        self.refresh_builder_ui()

    def refresh_builder_ui(self):
        for w in self.builder_scroll.winfo_children(): w.destroy()
        for mat_name, mat_data in self.project_materials.items():
            m_frame = ctk.CTkFrame(self.builder_scroll, fg_color="#1e3d59")
            m_frame.pack(fill="x", pady=2, padx=5)
            ctk.CTkLabel(m_frame, text=f"📦 {mat_name}", font=("Arial", 13, "bold")).pack(side="left", padx=10)

    def setup_inspector_panel(self):
        self.inspector_frame = ctk.CTkFrame(self.main_container, fg_color="#121212")
        self.inspector_frame.grid(row=0, column=2, sticky="nsew", padx=2)
        ctk.CTkLabel(self.inspector_frame, text="3. INSPECTOR", font=("Arial", 14, "bold")).pack(pady=10)
        self.dynamic_frame = ctk.CTkScrollableFrame(self.inspector_frame, fg_color="transparent")
        self.dynamic_frame.pack(fill="both", expand=True, padx=10)

if __name__ == "__main__":
    app = SignumSentinelGUI()
    app.mainloop()