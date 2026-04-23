import os
import json
import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
from PIL import Image
import psutil

try: import GPUtil
except ImportError: GPUtil = None

try:
    from core.import_assistant import AdvancedImporter
    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

if HAS_DND:
    class DnDWindow(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    class DnDWindow(ctk.CTk): pass


class SignumSentinelGUI(DnDWindow):
    def __init__(self):
        super().__init__()
        self.title("DVAMOCLES SWORD™ | MASTER DATA FORGE")
        self.geometry("1800x950")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.importer = AdvancedImporter(Path.cwd()) if HAS_BACKEND else None
        self.config_file = Path("config/gui_state.json")
        
        self.staged_groups = {} 
        self.project_materials = self.importer.load_existing_vault() if self.importer else {}
        self.active_selection = {"type": None, "id": None} 
        self.tree_state = self._load_gui_state()
        
        self.dragged_item_type = None 
        self.dragged_item_data = None
        self.drop_targets_geometry = [] 

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

    def _load_gui_state(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f: return json.load(f)
            except: pass
        return {}

    def _save_gui_state(self):
        if not self.config_file.parent.exists(): self.config_file.parent.mkdir()
        with open(self.config_file, "w") as f: json.dump(self.tree_state, f)

    def toggle_tree(self, id_str):
        self.tree_state[id_str] = not self.tree_state.get(id_str, True)
        self._save_gui_state()
        self.refresh_builder_ui()

    def setup_telemetry_bar(self):
        self.telemetry_frame = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#0a0a0a")
        self.telemetry_frame.pack(fill="x", side="top")
        self.lbl_cpu = ctk.CTkLabel(self.telemetry_frame, text="CPU: 0%", font=("Courier", 12, "bold"), text_color="#00e676")
        self.lbl_cpu.pack(side="left", padx=20)
        self.lbl_ram = ctk.CTkLabel(self.telemetry_frame, text="RAM: 0%", font=("Courier", 12, "bold"), text_color="#00b0ff")
        self.lbl_ram.pack(side="left", padx=20)
        self.lbl_gpu = ctk.CTkLabel(self.telemetry_frame, text="GPU: N/A", font=("Courier", 12, "bold"), text_color="#ff1744")
        self.lbl_gpu.pack(side="left", padx=20)

    def update_telemetry(self):
        self.lbl_cpu.configure(text=f"CPU: {psutil.cpu_percent()}%")
        self.lbl_ram.configure(text=f"RAM: {psutil.virtual_memory().percent}%")
        if GPUtil:
            gpus = GPUtil.getGPUs()
            if gpus: self.lbl_gpu.configure(text=f"GPU: {gpus[0].load*100:.1f}% | TEMP: {gpus[0].temperature}°C")
        self.after(2000, self.update_telemetry)

    # ==========================================
    # 1. STAGING PANEL
    # ==========================================
    def setup_staging_panel(self):
        self.staging_frame = ctk.CTkFrame(self.main_container, fg_color="#121212", corner_radius=0)
        self.staging_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        
        hdr = ctk.CTkFrame(self.staging_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(hdr, text="1. ASSET BROWSER", font=("Orbitron", 14, "bold")).pack(side="left")
        self.add_btn = ctk.CTkSegmentedButton(hdr, values=["+ Files", "+ Folder"], command=self.handle_add_btn)
        self.add_btn.pack(side="right", padx=5)

        self.auto_sort_btn = ctk.CTkButton(self.staging_frame, text="✨ AI AUTO-CREATE & SORT", fg_color="#6200ea", hover_color="#3700b3", command=self.execute_auto_sort)
        
        self.stage_scroll = ctk.CTkScrollableFrame(self.staging_frame, fg_color="#1e1e1e")
        self.stage_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        if HAS_DND:
            self.stage_scroll.drop_target_register(DND_FILES)
            self.stage_scroll.dnd_bind('<<Drop>>', self.on_drop_os)

    def handle_add_btn(self, value):
        if value == "+ Files":
            paths = filedialog.askopenfilenames(parent=self)
            if paths: self._process_input_paths(paths)
        elif value == "+ Folder":
            folder = filedialog.askdirectory(parent=self)
            if folder: self._process_input_paths([folder])
        self.add_btn.set("")

    def on_drop_os(self, event):
        import re
        paths = [p.strip('{}') for p in re.findall(r'\{.*?\}|\S+', event.data)]
        self._process_input_paths(paths)

    def _process_input_paths(self, paths):
        valid_ext = {'.png', '.jpg', '.jpeg', '.tif', '.exr', '.tga'}
        for p_str in paths:
            path = Path(p_str)
            if path.is_file() and path.suffix.lower() in valid_ext:
                if "Loose_Files" not in self.staged_groups: self.staged_groups["Loose_Files"] = []
                file_data = self.importer.auto_detect_file(str(path)) if self.importer else {"name": path.name, "path": str(path), "is_custom":False}
                self.staged_groups["Loose_Files"].append(file_data)
            elif path.is_dir():
                for f in path.rglob("*"):
                    if f.is_file() and f.suffix.lower() in valid_ext:
                        rel_path = f.parent.relative_to(path.parent)
                        group_name = str(rel_path)
                        if group_name not in self.staged_groups: self.staged_groups[group_name] = []
                        file_data = self.importer.auto_detect_file(str(f)) if self.importer else {"name": f.name, "path": str(f), "is_custom":False}
                        self.staged_groups[group_name].append(file_data)
        
        self.auto_sort_btn.pack(fill="x", padx=10, pady=(0,5), before=self.stage_scroll)
        self.refresh_staging_ui()

    def refresh_staging_ui(self):
        for widget in self.stage_scroll.winfo_children(): widget.destroy()

        for group_name, files in list(self.staged_groups.items()):
            if not files: 
                del self.staged_groups[group_name]
                continue
            
            g_frame = ctk.CTkFrame(self.stage_scroll, fg_color="#2c2c2c", corner_radius=5)
            g_frame.pack(fill="x", pady=5, padx=2)
            
            h_frame = ctk.CTkFrame(g_frame, fg_color="transparent")
            h_frame.pack(fill="x")
            
            g_lbl = ctk.CTkLabel(h_frame, text=f"📁 {group_name}", font=("Arial", 12, "bold"))
            g_lbl.pack(side="left", padx=10, pady=5)
            
            g_lbl.bind("<ButtonPress-1>", lambda e, gn=group_name: self.on_drag_start(e, "folder", gn))
            g_lbl.bind("<ButtonRelease-1>", self.on_drag_release)

            for i, f_data in enumerate(files):
                f_frame = ctk.CTkFrame(g_frame, fg_color="#1a1a1a", corner_radius=0)
                f_frame.pack(fill="x", pady=1, padx=5)
                
                is_dupe = f_data.get("is_duplicate", False)
                has_error = f_data.get("map_type") == "Unknown" or f_data.get("resolution") == "Unknown"
                
                if is_dupe: color, tag = "#ff9800", "[DUPLICATE] "
                elif has_error: color, tag = "#ff5252", ""
                else: color, tag = "#dddddd", ""
                
                meta = f"[{f_data.get('map_type')} | {f_data.get('format')} | {f_data.get('resolution')}]"
                lbl = ctk.CTkLabel(f_frame, text=f"{tag}📄 {f_data['name']} {meta}", font=("Arial", 11), text_color=color, cursor="hand2")
                lbl.pack(side="left", padx=10, pady=2)
                
                file_id = f"staging|{group_name}|{i}"
                lbl.bind("<ButtonPress-1>", lambda e, fd=f_data, gn=group_name: self.on_drag_start(e, "file", (gn, fd)))
                lbl.bind("<ButtonRelease-1>", self.on_drag_release)
                
                btn_edit = ctk.CTkButton(f_frame, text="✏️", width=25, fg_color="transparent", command=lambda id_s=file_id: self.set_inspector("staged_file", id_s))
                btn_edit.pack(side="right", padx=5)
                btn_del = ctk.CTkButton(f_frame, text="🗑️", width=25, fg_color="transparent", hover_color="#d32f2f", command=lambda grp=group_name, fobj=f_data: self.delete_staged_item(grp, fobj))
                btn_del.pack(side="right")

    def delete_staged_item(self, group, file_obj):
        self.staged_groups[group].remove(file_obj)
        self.active_selection = {"type":None, "id":None}
        self.refresh_staging_ui()
        self.refresh_inspector_ui()
        if not any(len(files) > 0 for files in self.staged_groups.values()):
            self.auto_sort_btn.pack_forget()

    def guess_base_material_name(self, filename: str) -> str:
        stem = Path(filename).stem
        tags_to_remove = ["albedo", "color", "basecolor", "normal", "roughness", "metallic", "ao", "ambientocclusion", "height", "displacement", "opacity", "1k", "2k", "3k", "4k", "8k", "dx", "gl"]
        parts = stem.replace("-", "_").split("_")
        clean_parts = [p for p in parts if p.lower() not in tags_to_remove]
        if not clean_parts: return "New_Material"
        return "_".join(clean_parts)

    def execute_auto_sort(self):
        moved = 0
        for group, files in list(self.staged_groups.items()):
            for f in list(files): 
                if f.get("is_duplicate"): continue
                mat_name = self.guess_base_material_name(f["name"])
                
                if mat_name not in self.project_materials:
                    self.project_materials[mat_name] = {
                        "provider": "", "url":"", "tags": [], "desc": "", "technique": "", "extra_docs": [],
                        "folders": {"Root": {"is_custom":False, "format":"Auto", "resolution":"Auto", "files":[]}}
                    }
                elif "Root" not in self.project_materials[mat_name]["folders"]:
                    self.project_materials[mat_name]["folders"]["Root"] = {"is_custom":False, "format":"Auto", "resolution":"Auto", "files":[]}
                    
                f["auto_organized"] = True
                self.project_materials[mat_name]["folders"]["Root"]["files"].append(f)
                files.remove(f)
                moved += 1
                
        self.refresh_staging_ui()
        self.refresh_builder_ui()
        if not any(len(files) > 0 for files in self.staged_groups.values()):
            self.auto_sort_btn.pack_forget()
        messagebox.showinfo("AI Auto-Sort", f"{moved} file organizzati in modo intelligente!")

    # --- DRAG AND DROP ---
    def on_drag_start(self, event, item_type, item_data):
        self.dragged_item_type = item_type
        self.dragged_item_data = item_data
        self.configure(cursor="hand2")

    def on_drag_motion(self, event): pass

    def on_drag_release(self, event):
        self.configure(cursor="")
        if not self.dragged_item_data: return
        mouse_x, mouse_y = self.winfo_pointerx(), self.winfo_pointery()
        target_found = None
        
        for target in self.drop_targets_geometry:
            widget = target["widget"]
            try:
                x1, y1 = widget.winfo_rootx(), widget.winfo_rooty()
                x2, y2 = x1 + widget.winfo_width(), y1 + widget.winfo_height()
                if x1 <= mouse_x <= x2 and y1 <= mouse_y <= y2:
                    target_found = target
                    break
            except: continue

        if target_found:
            drop_type, mat_name, folder_name = target_found["id"]
            if self.dragged_item_type == "folder" and drop_type == "material":
                group_name = self.dragged_item_data
                files_to_move = self.staged_groups.pop(group_name)
                safe_folder = Path(group_name).name
                if safe_folder not in self.project_materials[mat_name]["folders"]:
                    self.project_materials[mat_name]["folders"][safe_folder] = {"is_custom":False, "format":"Auto", "resolution":"Auto", "files":[]}
                self.project_materials[mat_name]["folders"][safe_folder]["files"].extend(files_to_move)
            
            elif self.dragged_item_type == "file":
                src_group, file_data = self.dragged_item_data
                target_folder = "Root" if drop_type == "material" else folder_name
                self.project_materials[mat_name]["folders"][target_folder]["files"].append(file_data)
                self.staged_groups[src_group].remove(file_data)
            
            self.refresh_staging_ui()
            self.refresh_builder_ui()
        self.dragged_item_type, self.dragged_item_data = None, None

    # ==========================================
    # 2. PROJECT VAULT
    # ==========================================
    def setup_builder_panel(self):
        self.builder_frame = ctk.CTkFrame(self.main_container, fg_color="#161b22", corner_radius=0)
        self.builder_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)

        hdr = ctk.CTkFrame(self.builder_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=10, padx=10)
        ctk.CTkLabel(hdr, text="2. PROJECT VAULT", font=("Orbitron", 14, "bold")).pack(side="left")
        ctk.CTkButton(hdr, text="➕ Material", width=80, command=self.add_material).pack(side="right")

        self.builder_scroll = ctk.CTkScrollableFrame(self.builder_frame, fg_color="#0d1117")
        self.builder_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        self.refresh_builder_ui() 

    def add_material(self):
        name = simpledialog.askstring("Material", "Name:", parent=self)
        if name:
            safe = name.strip().replace(" ", "_")
            self.project_materials[safe] = {
                "provider": "", "url":"", "tags": [], "desc": "", "technique": "", "extra_docs": [],
                "folders": {} 
            }
            self.refresh_builder_ui()

    def add_folder(self, mat_name):
        f_name = simpledialog.askstring("Texture Set", f"Variant for {mat_name}:", parent=self)
        if f_name:
            self.project_materials[mat_name]["folders"][f_name.strip()] = {"is_custom":False, "desc":"", "format":"Auto", "resolution":"Auto", "files":[]}
            self.refresh_builder_ui()

    def set_inspector(self, type_, id_str):
        self.active_selection = {"type": type_, "id": id_str}
        self.refresh_inspector_ui()

    def delete_item(self, item_type, id_str):
        if not messagebox.askyesno("Confirm Delete", f"Delete {item_type} '{id_str}'?"): return
        if item_type == "material":
            for folder in self.project_materials[id_str]["folders"].values():
                for f in folder["files"]:
                    if not f.get("is_existing"): self.staged_groups.setdefault("Root_Files", []).append(f)
            del self.project_materials[id_str]
        elif item_type == "folder":
            mat_name, f_name = id_str.split("|")
            for f in self.project_materials[mat_name]["folders"][f_name]["files"]:
                if not f.get("is_existing"): self.staged_groups.setdefault("Root_Files", []).append(f)
            del self.project_materials[mat_name]["folders"][f_name]
        elif item_type == "file":
            mat_name, f_name, f_idx = id_str.split("|")
            f_data = self.project_materials[mat_name]["folders"][f_name]["files"].pop(int(f_idx))
            if not f_data.get("is_existing"): self.staged_groups.setdefault("Root_Files", []).append(f_data)

        self.active_selection = {"type":None, "id":None}
        self.refresh_staging_ui()
        self.refresh_builder_ui()
        self.refresh_inspector_ui()

    def refresh_builder_ui(self):
        for widget in self.builder_scroll.winfo_children(): widget.destroy()
        self.drop_targets_geometry.clear() 

        for mat_name, mat_data in self.project_materials.items():
            m_frame = ctk.CTkFrame(self.builder_scroll, fg_color="#1e3d59", corner_radius=5)
            m_frame.pack(fill="x", pady=5, padx=5)
            
            hdr_f = ctk.CTkFrame(m_frame, fg_color="transparent")
            hdr_f.pack(fill="x", padx=5, pady=5)
            
            is_open = self.tree_state.get(mat_name, False)
            ctk.CTkButton(hdr_f, text="▼" if is_open else "▶", width=20, fg_color="transparent", command=lambda m=mat_name: self.toggle_tree(m)).pack(side="left")
            
            m_lbl = ctk.CTkLabel(hdr_f, text=f"📦 {mat_name}", font=("Arial", 14, "bold"), cursor="hand2")
            m_lbl.pack(side="left", padx=5)
            m_lbl.bind("<Button-1>", lambda e, m=mat_name: self.set_inspector("material", m))
            
            ctk.CTkButton(hdr_f, text="🗑️", width=30, fg_color="transparent", command=lambda m=mat_name: self.delete_item("material", m)).pack(side="right")
            ctk.CTkButton(hdr_f, text="➕ Set", width=50, height=20, fg_color="#000000", command=lambda m=mat_name: self.add_folder(m)).pack(side="right", padx=5)
            
            self.drop_targets_geometry.append({"widget": m_frame, "id": ("material", mat_name, None)})

            if not is_open: continue

            for folder_name, folder_data in mat_data["folders"].items():
                v_frame = ctk.CTkFrame(m_frame, fg_color="#1a1a1a")
                v_frame.pack(fill="x", padx=10, pady=2)
                
                f_hdr = ctk.CTkFrame(v_frame, fg_color="transparent")
                f_hdr.pack(fill="x")
                
                fid = f"{mat_name}|{folder_name}"
                f_is_open = self.tree_state.get(fid, True)
                ctk.CTkButton(f_hdr, text="▼" if f_is_open else "▶", width=20, fg_color="transparent", command=lambda i=fid: self.toggle_tree(i)).pack(side="left")
                
                c_color = "#ff5252" if folder_data.get("is_custom") else "#00b0ff"
                f_lbl = ctk.CTkLabel(f_hdr, text=f"📂 {folder_name}", font=("Arial", 12, "bold"), text_color=c_color, cursor="hand2")
                f_lbl.pack(side="left", padx=5, pady=2)
                f_lbl.bind("<Button-1>", lambda e, id_s=fid: self.set_inspector("folder", id_s))
                ctk.CTkButton(f_hdr, text="🗑️", width=30, fg_color="transparent", command=lambda i=fid: self.delete_item("folder", i)).pack(side="right")
                
                self.drop_targets_geometry.append({"widget": v_frame, "id": ("folder", mat_name, folder_name)})

                if not f_is_open: continue

                for i, f_obj in enumerate(folder_data["files"]):
                    file_id = f"{mat_name}|{folder_name}|{i}"
                    
                    if f_obj.get("is_existing"): file_color = "#5c5c5c"
                    elif f_obj.get("is_custom"): file_color = "#ff8a80"
                    elif f_obj.get("auto_organized"): file_color = "#00e676" 
                    else: file_color = "#aaaaaa"
                    
                    fi_f = ctk.CTkFrame(v_frame, fg_color="transparent")
                    fi_f.pack(fill="x")
                    
                    has_error = (f_obj.get("map_type") == "Unknown") or (f_obj.get("resolution") == "Unknown" and folder_data.get("resolution") == "Auto")
                    if has_error and not f_obj.get("is_existing"): file_color = "#ff1744"
                    
                    real_name = Path(f_obj.get('path', f_obj['name'])).name
                    fmt_res = f"[{f_obj.get('map_type')} | {f_obj.get('format')} | {f_obj.get('resolution')}]"
                    lbl = ctk.CTkLabel(fi_f, text=f"   ↳ 📄 {real_name} {fmt_res}", text_color=file_color, cursor="hand2")
                    lbl.pack(side="left", padx=5)
                    lbl.bind("<Button-1>", lambda e, id_s=file_id: self.set_inspector("file", id_s))
                    ctk.CTkButton(fi_f, text="X", width=20, fg_color="transparent", hover_color="#d32f2f", command=lambda i=file_id: self.delete_item("file", i)).pack(side="right")

    # ==========================================
    # 3. DYNAMIC INSPECTOR 
    # ==========================================
    def setup_inspector_panel(self):
        self.inspector_frame = ctk.CTkFrame(self.main_container, fg_color="#121212", corner_radius=0)
        self.inspector_frame.grid(row=0, column=2, sticky="nsew", padx=2, pady=2)
        
        self.ins_header = ctk.CTkLabel(self.inspector_frame, text="3. METADATA INSPECTOR", font=("Orbitron", 14, "bold"))
        self.ins_header.pack(pady=10)
        
        self.dynamic_frame = ctk.CTkScrollableFrame(self.inspector_frame, fg_color="transparent")
        self.dynamic_frame.pack(fill="both", expand=True, padx=10)
        
        self.import_btn = ctk.CTkButton(self.inspector_frame, text="EXECUTE FORGE", fg_color="#d32f2f", height=40, font=("Arial", 16, "bold"), command=self.start_forge)
        self.import_btn.pack(side="bottom", fill="x", padx=20, pady=20)

    def render_tags_ui(self, parent_frame, tags_list):
        tags_container = ctk.CTkFrame(parent_frame, fg_color="transparent")
        tags_container.pack(fill="x", pady=2)
        for t in tags_list:
            ctk.CTkButton(tags_container, text=f"{t} ✕", width=40, height=20, fg_color="#00695c", command=lambda tag=t: self.remove_tag(tag)).pack(side="left", padx=2, pady=2)
        entry = ctk.CTkEntry(parent_frame, placeholder_text="Type tag & press Enter...")
        entry.pack(fill="x", pady=2)
        entry.bind("<Return>", lambda e: self.add_tag(entry.get(), entry))

    def add_tag(self, tag, entry):
        tag = tag.strip()
        if tag and self.active_selection["type"] == "material":
            mat = self.project_materials[self.active_selection["id"]]
            if tag not in mat["tags"]: mat["tags"].append(tag)
        entry.delete(0, 'end')
        self.refresh_inspector_ui()

    def remove_tag(self, tag):
        self.project_materials[self.active_selection["id"]]["tags"].remove(tag)
        self.refresh_inspector_ui()

    def refresh_inspector_ui(self):
        for widget in self.dynamic_frame.winfo_children(): widget.destroy()
        stype = self.active_selection["type"]
        sid = self.active_selection["id"]
        if not stype: return

        ui_prefs = self.importer.ui_prefs if self.importer else {"providers":[], "formats":[], "resolutions":[], "map_types":[]}

        if stype == "material":
            mat = self.project_materials[sid]
            self.ins_header.configure(text=f"MATERIAL: {sid}")
            
            ctk.CTkLabel(self.dynamic_frame, text="Provider:").pack(anchor="w")
            self.p_prov = ctk.CTkComboBox(self.dynamic_frame, values=ui_prefs.get("providers", []))
            self.p_prov.set(mat.get("provider", ""))
            self.p_prov.pack(fill="x", pady=2)
            
            ctk.CTkLabel(self.dynamic_frame, text="Technique:").pack(anchor="w")
            self.p_tech = ctk.CTkComboBox(self.dynamic_frame, values=["Photogrammetry", "Procedural", "AI Generated", "Scanned"])
            self.p_tech.set(mat.get("technique", ""))
            self.p_tech.pack(fill="x", pady=2)
            
            ctk.CTkLabel(self.dynamic_frame, text="Tags:").pack(anchor="w", pady=(10,0))
            self.render_tags_ui(self.dynamic_frame, mat.get("tags", []))
            
            ctk.CTkButton(self.dynamic_frame, text="Save Material", command=lambda: self._save_mat(sid)).pack(pady=10)

        elif stype == "folder":
            mat_name, f_name = sid.split("|")
            folder = self.project_materials[mat_name]["folders"][f_name]
            self.ins_header.configure(text=f"FOLDER: {f_name}")
            
            self.f_custom_var = ctk.BooleanVar(value=folder.get("is_custom", False))
            sw = ctk.CTkSwitch(self.dynamic_frame, text="IS CUSTOM", variable=self.f_custom_var, command=lambda: self._save_folder(mat_name, f_name, True))
            sw.pack(anchor="w", pady=10)
            
            if self.f_custom_var.get():
                ctk.CTkLabel(self.dynamic_frame, text="Process Workflow:").pack(anchor="w")
                self.f_proc = ctk.CTkEntry(self.dynamic_frame)
                self.f_proc.insert(0, folder.get("process", ""))
                self.f_proc.pack(fill="x", pady=2)
            else:
                ctk.CTkLabel(self.dynamic_frame, text="Apply Resolution to all files:").pack(anchor="w")
                self.f_res = ctk.CTkComboBox(self.dynamic_frame, values=ui_prefs.get("resolutions", []))
                self.f_res.set(folder.get("resolution", "Auto"))
                self.f_res.pack(fill="x", pady=2)
                
                ctk.CTkLabel(self.dynamic_frame, text="Apply Format to all files:").pack(anchor="w")
                self.f_form = ctk.CTkComboBox(self.dynamic_frame, values=ui_prefs.get("formats", []))
                self.f_form.set(folder.get("format", "Auto"))
                self.f_form.pack(fill="x", pady=2)
                
            ctk.CTkButton(self.dynamic_frame, text="Save Folder", command=lambda: self._save_folder(mat_name, f_name)).pack(pady=10)

        elif stype in ["file", "staged_file"]:
            is_staged = (stype == "staged_file")
            if is_staged:
                _, grp, idx_str = sid.split("|")
                f_idx = int(idx_str)
                f_obj = self.staged_groups[grp][f_idx]
            else:
                mat_name, f_name, f_idx_str = sid.split("|")
                f_idx = int(f_idx_str)
                f_obj = self.project_materials[mat_name]["folders"][f_name]["files"][f_idx]
                
            self.ins_header.configure(text=f"FILE: {Path(f_obj.get('path', f_obj['name'])).name}")
            
            if "tech_res" in f_obj:
                tech_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="#1a1a1a")
                tech_frame.pack(fill="x", pady=5)
                ctk.CTkLabel(tech_frame, text=f"🧬 PHYSICAL METADATA", font=("Arial", 10, "bold"), text_color="#00e676").pack(anchor="w", padx=5)
                ctk.CTkLabel(tech_frame, text=f"Pixels: {f_obj.get('tech_res')} | Bit: {f_obj.get('bit_depth')} | Color: {f_obj.get('color_space')}", font=("Arial", 11)).pack(anchor="w", padx=5, pady=2)

            self.fi_custom_var = ctk.BooleanVar(value=f_obj.get("is_custom", False))
            ctk.CTkSwitch(self.dynamic_frame, text="IS CUSTOM", variable=self.fi_custom_var).pack(anchor="w", pady=10)
            
            ctk.CTkLabel(self.dynamic_frame, text="Map Type:").pack(anchor="w")
            
            saved_map = f_obj.get("map_type", "Unknown").upper()
            display_map = "NORMAL" if saved_map.startswith("NORMAL") else saved_map
            
            learned = []
            if self.importer:
                for p_dict in self.importer.learned_rules.values(): learned.extend(p_dict.values())
            suggestions = list(set([x.split("_")[0] for x in ui_prefs.get("map_types", [])] + [x.split("_")[0] for x in learned]))
            if "NORMAL" not in suggestions: suggestions.append("NORMAL")
            
            self.fi_map = ctk.CTkComboBox(self.dynamic_frame, values=suggestions, command=self._check_normal)
            self.fi_map.set(display_map)
            self.fi_map.pack(fill="x", pady=2)
            self.fi_map.bind("<KeyRelease>", lambda e: self._check_normal())

            self.normal_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            ctk.CTkLabel(self.normal_frame, text="Normal Convention:").pack(anchor="w")
            self.fi_norm = ctk.CTkSegmentedButton(self.normal_frame, values=["DirectX", "OpenGL", "Unknown"])
            
            conv = "Unknown"
            if saved_map == "NORMAL_DX": conv = "DirectX"
            elif saved_map == "NORMAL_GL": conv = "OpenGL"
            self.fi_norm.set(conv)
            self.fi_norm.pack(fill="x", pady=2)
            self._check_normal()
            
            ctk.CTkLabel(self.dynamic_frame, text="Format:").pack(anchor="w", pady=(10,0))
            self.fi_form = ctk.CTkComboBox(self.dynamic_frame, values=ui_prefs.get("formats", []))
            self.fi_form.set(f_obj.get("format", "Unknown"))
            self.fi_form.pack(fill="x", pady=2)
            
            ctk.CTkLabel(self.dynamic_frame, text="Resolution:").pack(anchor="w")
            self.fi_res = ctk.CTkComboBox(self.dynamic_frame, values=ui_prefs.get("resolutions", []))
            self.fi_res.set(f_obj.get("resolution", "Unknown"))
            self.fi_res.pack(fill="x", pady=2)

            if is_staged:
                ctk.CTkButton(self.dynamic_frame, text="Save Staged File & Learn", command=lambda: self._save_staged_file(grp, f_idx)).pack(pady=10)
            else:
                ctk.CTkButton(self.dynamic_frame, text="Save File & Learn", command=lambda: self._save_file(mat_name, f_name, f_idx)).pack(pady=10)

    def _check_normal(self, *args):
        if self.fi_map.get().upper() == "NORMAL": self.normal_frame.pack(fill="x", pady=5, after=self.fi_map)
        else: self.normal_frame.pack_forget()

    def _save_mat(self, mat_name):
        new_prov = self.p_prov.get()
        self.project_materials[mat_name]["provider"] = new_prov
        self.project_materials[mat_name]["technique"] = self.p_tech.get()
        if self.importer: self.importer.add_ui_pref("providers", new_prov)
        self.refresh_builder_ui()

    def _save_folder(self, mat_name, f_name, refresh_only=False):
        folder = self.project_materials[mat_name]["folders"][f_name]
        folder["is_custom"] = self.f_custom_var.get()
        if not refresh_only:
            if folder["is_custom"]: folder["process"] = self.f_proc.get().strip()
            else:
                folder["resolution"] = self.f_res.get()
                folder["format"] = self.f_form.get()
                if self.importer:
                    self.importer.add_ui_pref("resolutions", folder["resolution"])
                    self.importer.add_ui_pref("formats", folder["format"])
        self.refresh_builder_ui()
        if refresh_only: self.refresh_inspector_ui()

    def _save_file(self, mat_name, f_name, f_idx):
        f_obj = self.project_materials[mat_name]["folders"][f_name]["files"][f_idx]
        self._apply_file_save(f_obj)
        self.refresh_builder_ui()

    def _save_staged_file(self, grp, f_idx):
        f_obj = self.staged_groups[grp][f_idx]
        self._apply_file_save(f_obj)
        self.refresh_staging_ui()

    def _apply_file_save(self, f_obj):
        f_obj["is_custom"] = self.fi_custom_var.get()
        
        new_map_type = self.fi_map.get().upper()
        if new_map_type == "NORMAL":
            conv = self.fi_norm.get()
            if conv == "DirectX": new_map_type = "NORMAL_DX"
            elif conv == "OpenGL": new_map_type = "NORMAL_GL"

        old_map_type = f_obj.get("map_type", "Unknown")
        f_obj["map_type"] = new_map_type
        f_obj["format"] = self.fi_form.get().upper()
        f_obj["resolution"] = self.fi_res.get().upper()
        
        if self.importer:
            self.importer.add_ui_pref("map_types", "NORMAL" if new_map_type.startswith("NORMAL") else new_map_type)
            self.importer.add_ui_pref("formats", f_obj["format"])
            self.importer.add_ui_pref("resolutions", f_obj["resolution"])
        
        if new_map_type != old_map_type and new_map_type != "UNKNOWN":
            suffix = self.importer.extract_suffix(Path(f_obj.get("path", f_obj["name"])).name) if self.importer else ""
            if suffix and messagebox.askyesno("Apprendimento", f"Vuoi applicare '{new_map_type}' a tutti i file che terminano in '{suffix}'?"):
                for m_data in self.project_materials.values():
                    for folder in m_data["folders"].values():
                        for file in folder["files"]:
                            if Path(file.get("path", file["name"])).name.lower().endswith(suffix): file["map_type"] = new_map_type
                for group, files in self.staged_groups.items():
                    for f in files:
                        if Path(f.get("path", f["name"])).name.lower().endswith(suffix): f["map_type"] = new_map_type

    def start_forge(self):
        if not HAS_BACKEND: return
        for mat_name, m_data in self.project_materials.items():
            for f_name, folder in m_data["folders"].items():
                f_res = folder.get("resolution", "Auto")
                f_form = folder.get("format", "Auto")
                for i, file in enumerate(folder["files"]):
                    if file.get("is_existing"): continue 
                    if file["map_type"] == "Unknown":
                        messagebox.showerror("Validation", f"[{file['name']}] Map Type mancante.")
                        self.set_inspector("file", f"{mat_name}|{f_name}|{i}")
                        return
                    if file["resolution"] == "Unknown" and f_res == "Auto":
                        messagebox.showerror("Validation", f"[{file['name']}] Risoluzione mancante.")
                        self.set_inspector("file", f"{mat_name}|{f_name}|{i}")
                        return
                    if file["format"] == "Unknown" and f_form == "Auto":
                        messagebox.showerror("Validation", f"[{file['name']}] Formato mancante.")
                        self.set_inspector("file", f"{mat_name}|{f_name}|{i}")
                        return

        res = self.importer.run_import({"materials": self.project_materials})
        if res["status"] == "success":
            messagebox.showinfo("Forge Complete", res["message"])
            self.project_materials = self.importer.load_existing_vault()
            self.staged_groups.clear()
            self.refresh_builder_ui()
            self.refresh_staging_ui()
            self.refresh_inspector_ui()
        else: messagebox.showerror("Error", res["message"])

if __name__ == "__main__":
    app = SignumSentinelGUI()
    app.mainloop()