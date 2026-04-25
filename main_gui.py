import gc
import json
import os
import re
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import customtkinter as ctk
import psutil
from difflib import SequenceMatcher

try:
    from core.import_assistant import AdvancedImporter

    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False

try:
    import GPUtil
except ImportError:
    GPUtil = None

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAS_DND = True
except ImportError:
    HAS_DND = False

STAGING_SCAN_MAX_DEPTH = 3
COLOR_RAW = "#6b6b6b"
COLOR_CUSTOM = "#9b59b6"
COLOR_ACCENT = "#6200ea"


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
    """SIGNUM SENTINEL — tre pannelli: Staging, Vault, Metadata Inspector."""

    def __init__(self):
        super().__init__()

        self.title("DVAMOCLES SWORD™ | SIGNUM SENTINEL")
        self.geometry("1880x980")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.root_path = Path.cwd()
        self.importer = AdvancedImporter(self.root_path) if HAS_BACKEND else None

        self.staging_project: dict = {}
        self.project_materials: dict = (
            self.importer.load_existing_vault() if self.importer else {}
        )
        self.tree_state = self._load_state()
        self.selection = {
            "scope": None,
            "material": None,
            "variant": None,
            "file": None,
        }

        self.staging_dir = self.root_path / "temp" / "staging_asset_browser"
        self.staging_dir.mkdir(parents=True, exist_ok=True)

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
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _load_state(self):
        p = Path("config/gui_state.json")
        if p.exists():
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_state(self):
        os.makedirs("config", exist_ok=True)
        with open("config/gui_state.json", "w", encoding="utf-8") as f:
            json.dump(self.tree_state, f, indent=2)

    def on_closing(self):
        if messagebox.askokcancel("Esci", "Chiudere e liberare la VRAM?"):
            if self.importer:
                self.importer.unload_ai()
            self._save_state()
            self.destroy()

    def setup_telemetry_bar(self):
        self.telemetry_frame = ctk.CTkFrame(self, height=34, corner_radius=0, fg_color="#0a0a0a")
        self.telemetry_frame.pack(fill="x", side="top")

        self.lbl_cpu = ctk.CTkLabel(
            self.telemetry_frame,
            text="CPU: — | RAM: — | VRAM: —",
            font=("Consolas", 12),
        )
        self.lbl_cpu.pack(side="left", padx=16)

        self.ai_btn = ctk.CTkButton(
            self.telemetry_frame,
            text="IA: OFF",
            width=72,
            fg_color="#333",
            command=self.toggle_ai,
        )
        self.ai_btn.pack(side="right", padx=10)

    def toggle_ai(self):
        if not self.importer:
            return
        if self.importer.ai_model is None:
            self.importer.load_ai()
            self.ai_btn.configure(text="IA: ON", fg_color=COLOR_ACCENT)
        else:
            self.importer.unload_ai()
            self.ai_btn.configure(text="IA: OFF", fg_color="#333")

    def _vram_percent(self):
        if GPUtil is None:
            return None
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return None
            g = gpus[0]
            return 100.0 * (g.memoryUsed / max(g.memoryTotal, 1))
        except Exception:
            return None

    def update_telemetry(self):
        ram = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent()
        vram = self._vram_percent()
        vram_txt = f"{vram:.0f}%" if vram is not None else "n/d"
        warn = ""
        if vram is not None and vram > 88:
            warn = " ⚠ VRAM ALTA"
        if ram > 90:
            warn += " ⚠ RAM ALTA"
        self.lbl_cpu.configure(text=f"CPU: {cpu:.0f}% | RAM: {ram:.0f}% | VRAM: {vram_txt}{warn}")
        self.after(2500, self.update_telemetry)

    # --- Panel 1: Staging ---
    def setup_staging_panel(self):
        self.staging_frame = ctk.CTkFrame(self.main_container, fg_color="#121212")
        self.staging_frame.grid(row=0, column=0, sticky="nsew", padx=2)

        hdr = ctk.CTkFrame(self.staging_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=10)
        ctk.CTkLabel(hdr, text="1. ASSET BROWSER (Staging)", font=("Segoe UI", 14, "bold")).pack(
            side="left", padx=10
        )
        ctk.CTkButton(hdr, text="+ Cartella", width=90, command=self.browse_folder).pack(side="right", padx=6)

        self.sort_container = ctk.CTkFrame(self.staging_frame, fg_color="transparent")
        self.sort_container.pack(fill="x", padx=10)
        self.auto_sort_btn = ctk.CTkButton(
            self.sort_container,
            text="✨ AUTO-SORT (fuzzy → Vault)",
            fg_color=COLOR_ACCENT,
            command=self.execute_auto_sort,
        )

        ctk.CTkLabel(
            self.staging_frame,
            text="Staging logico (max 3 livelli sotto la cartella droppata). RAW=grigio.",
            font=("Segoe UI", 10),
            text_color="#888",
        ).pack(anchor="w", padx=12)

        self.stage_scroll = ctk.CTkScrollableFrame(self.staging_frame, fg_color="#1e1e1e")
        self.stage_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        if HAS_DND:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind("<<Drop>>", self.on_drop)
            except Exception as exc:
                print(f"DnD: {exc}")

    def browse_folder(self):
        initial = self.tree_state.get("last_import_dir") or str(self.root_path)
        folder = filedialog.askdirectory(initialdir=initial)
        if folder:
            self.tree_state["last_import_dir"] = folder
            self._process_paths([folder])

    def on_drop(self, event):
        paths = [p.strip("{}") for p in re.findall(r"\{.*?\}|\S+", event.data)]
        if paths:
            self.tree_state["last_import_dir"] = str(Path(paths[0]).parent)
        self._process_paths(paths)

    def _merge_staging_project(self, new_project: dict) -> None:
        for mat, data in new_project.items():
            if mat not in self.staging_project:
                self.staging_project[mat] = {
                    "provider": data.get("provider", "UnknownProvider"),
                    "asset_type": data.get("asset_type", "RAW"),
                    "tags": list(data.get("tags", [])),
                    "desc": data.get("desc", ""),
                    "process_description": data.get("process_description", ""),
                    "relationships": list(data.get("relationships", [])),
                    "folders": {},
                }
            tgt = self.staging_project[mat]
            for vname, vdata in data.get("folders", {}).items():
                slot = tgt["folders"].setdefault(
                    vname,
                    {
                        "is_custom": vdata.get("is_custom", False),
                        "variant_tags": vdata.get("variant_tags", []),
                        "files": [],
                    },
                )
                seen = {f"{f.get('name', '')}|{f.get('tech_res', '')}" for f in slot["files"]}
                for f in vdata.get("files", []):
                    key = f"{f.get('name', '')}|{f.get('tech_res', '')}"
                    if key not in seen:
                        slot["files"].append(f)
                        seen.add(key)

    def _process_paths(self, paths):
        if not self.importer:
            messagebox.showerror("Backend", "AdvancedImporter non disponibile.")
            return
        new_proj = self.importer.ingest_paths(paths, max_depth=STAGING_SCAN_MAX_DEPTH)
        self._merge_staging_project(new_proj)
        if self.staging_project:
            self.auto_sort_btn.pack(fill="x", pady=5)
        self.refresh_staging_ui()

    def refresh_staging_ui(self):
        for w in self.stage_scroll.winfo_children():
            w.destroy()
        for mat, data in sorted(self.staging_project.items()):
            g_frame = ctk.CTkFrame(self.stage_scroll, fg_color="#2c2c2c")
            g_frame.pack(fill="x", pady=2, padx=2)
            ctk.CTkLabel(g_frame, text=f"◆ {mat}", font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10)
            for vname, vdata in sorted(data.get("folders", {}).items()):
                is_c = vdata.get("is_custom", False)
                col = COLOR_CUSTOM if is_c else COLOR_RAW
                vf = ctk.CTkFrame(g_frame, fg_color="#252525")
                vf.pack(fill="x", padx=8, pady=2)
                tags = vdata.get("variant_tags") or []
                tag_txt = " · ".join(tags) if tags else vname
                lbl = ctk.CTkLabel(
                    vf,
                    text=f"  └ Texture set: {vname}  ({tag_txt})",
                    font=("Segoe UI", 11),
                    text_color=col,
                )
                lbl.pack(anchor="w", padx=6)
                lbl.bind(
                    "<Button-1>",
                    lambda _e, m=mat, v=vname: self._select_variant("staging", m, v, None),
                )
                for f in vdata.get("files", []):
                    ff = ctk.CTkFrame(vf, fg_color="#1a1a1a")
                    ff.pack(fill="x", pady=1, padx=10)
                    meta = f"[{f.get('map_type')} | {f.get('tech_res')}] {f.get('visual_validation', '')}"
                    fl = ctk.CTkLabel(ff, text=f"    📄 {f['name']}  {meta}", font=("Segoe UI", 10))
                    fl.pack(side="left", padx=4)
                    fl.bind(
                        "<Button-1>",
                        lambda _e, m=mat, v=vname, file=f: self._select_file("staging", m, v, file),
                    )

    # --- Panel 2: Vault ---
    def setup_builder_panel(self):
        self.builder_frame = ctk.CTkFrame(self.main_container, fg_color="#161b22")
        self.builder_frame.grid(row=0, column=1, sticky="nsew", padx=2)
        ctk.CTkLabel(self.builder_frame, text="2. PROJECT VAULT", font=("Segoe UI", 14, "bold")).pack(pady=10)
        self.builder_scroll = ctk.CTkScrollableFrame(self.builder_frame, fg_color="#0d1117")
        self.builder_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        self.refresh_builder_ui()

    def _vault_context_menu(self, mat_name: str, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label="Aggiungi Texture Set vuoto…",
            command=lambda: self._prompt_add_texture_set(mat_name),
        )
        menu.add_command(
            label="Sposta materiale in Staging",
            command=lambda: self._move_material_to_staging(mat_name),
        )
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _prompt_add_texture_set(self, mat_name: str):
        name = simpledialog.askstring("Texture Set", "Nome cartella variante (es. 1K_PNG):", parent=self)
        if not name:
            return
        m = self.project_materials.setdefault(
            mat_name,
            {"provider": "Manual", "folders": {}, "tags": [], "desc": ""},
        )
        m["folders"].setdefault(
            name,
            {"is_custom": False, "variant_tags": self._tags_from_variant_key(name), "files": []},
        )
        self.refresh_builder_ui()

    def _move_material_to_staging(self, mat_name: str):
        if mat_name in self.project_materials:
            self._merge_staging_project({mat_name: self.project_materials.pop(mat_name)})
            self.refresh_staging_ui()
            self.refresh_builder_ui()

    @staticmethod
    def _tags_from_variant_key(vkey: str):
        if vkey in ("SOURCE", "Root"):
            return []
        parts = vkey.split("_", 1)
        out = []
        if parts and re.match(r"^\d+K$", parts[0], re.I):
            out.append(parts[0].upper())
        if len(parts) > 1:
            out.append(parts[1].upper())
        return out

    def refresh_builder_ui(self):
        for w in self.builder_scroll.winfo_children():
            w.destroy()
        for mat_name, mat_data in sorted(self.project_materials.items()):
            m_frame = ctk.CTkFrame(self.builder_scroll, fg_color="#1e3d59")
            m_frame.pack(fill="x", pady=2, padx=5)
            hl = ctk.CTkLabel(m_frame, text=f"📦 {mat_name}", font=("Segoe UI", 13, "bold"))
            hl.pack(side="left", padx=10)
            hl.bind("<Button-1>", lambda _e, m=mat_name: self._select_material("vault", m))
            hl.bind("<Button-3>", lambda e, m=mat_name: self._vault_context_menu(m, e))
            m_frame.bind("<Button-3>", lambda e, m=mat_name: self._vault_context_menu(m, e))

            for folder_name, fdata in sorted(mat_data.get("folders", {}).items()):
                is_c = fdata.get("is_custom", False)
                col = COLOR_CUSTOM if is_c else COLOR_RAW
                row = ctk.CTkFrame(m_frame, fg_color="transparent")
                row.pack(fill="x", padx=20, pady=1)
                vl = ctk.CTkLabel(
                    row,
                    text=f"  ▹ {folder_name}  ({len(fdata.get('files', []))} file)",
                    font=("Segoe UI", 11),
                    text_color=col,
                )
                vl.pack(side="left")
                vl.bind(
                    "<Button-1>",
                    lambda _e, m=mat_name, v=folder_name: self._select_variant("vault", m, v, None),
                )

    # --- Panel 3: Inspector ---
    def setup_inspector_panel(self):
        self.inspector_frame = ctk.CTkFrame(self.main_container, fg_color="#121212")
        self.inspector_frame.grid(row=0, column=2, sticky="nsew", padx=2)
        ctk.CTkLabel(self.inspector_frame, text="3. METADATA INSPECTOR", font=("Segoe UI", 14, "bold")).pack(
            pady=10
        )
        self.dynamic_frame = ctk.CTkScrollableFrame(self.inspector_frame, fg_color="transparent")
        self.dynamic_frame.pack(fill="both", expand=True, padx=10)
        self._refresh_inspector_placeholder()

    def _refresh_inspector_placeholder(self):
        for w in self.dynamic_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.dynamic_frame,
            text="Seleziona un materiale, un texture set o un file.",
            font=("Segoe UI", 11),
            text_color="#777",
        ).pack(anchor="w", pady=6)

    def _select_material(self, scope, mat):
        self.selection = {"scope": scope, "material": mat, "variant": None, "file": None}
        self._render_inspector_material(mat)

    def _select_variant(self, scope, mat, variant, _file):
        self.selection = {"scope": scope, "material": mat, "variant": variant, "file": None}
        self._render_inspector_variant(scope, mat, variant)

    def _select_file(self, scope, mat, variant, file_obj):
        self.selection = {"scope": scope, "material": mat, "variant": variant, "file": file_obj}
        self._render_inspector_file(scope, mat, variant, file_obj)

    def _material_blob(self, scope, mat):
        if scope == "staging":
            return self.staging_project.get(mat, {})
        return self.project_materials.get(mat, {})

    def _render_inspector_material(self, mat):
        for w in self.dynamic_frame.winfo_children():
            w.destroy()
        blob = self._material_blob(self.selection["scope"], mat)
        ctk.CTkLabel(self.dynamic_frame, text=f"Materiale: {mat}", font=("Segoe UI", 13, "bold")).pack(
            anchor="w", pady=4
        )

        prov = ctk.CTkEntry(self.dynamic_frame, placeholder_text="Provider")
        prov.insert(0, blob.get("provider", ""))
        prov.pack(fill="x", pady=2)
        self._inspector_field("provider", prov)

        at_var = tk.StringVar(value=blob.get("asset_type", "RAW"))
        seg = ctk.CTkSegmentedButton(
            self.dynamic_frame,
            values=["RAW", "CUSTOM"],
            variable=at_var,
        )
        seg.pack(fill="x", pady=6)
        self._inspector_field("asset_type_seg", seg)
        self._inspector_field("asset_type_var", at_var)

        tags_e = ctk.CTkEntry(self.dynamic_frame, placeholder_text="Tag (virgola)")
        tags_e.insert(0, ", ".join(blob.get("tags", [])))
        tags_e.pack(fill="x", pady=2)
        self._inspector_field("tags", tags_e)

        pd = ctk.CTkTextbox(self.dynamic_frame, height=72)
        pd.pack(fill="x", pady=4)
        pd.insert("1.0", blob.get("process_description", ""))
        self._inspector_field("process_desc", pd)

        ctk.CTkButton(
            self.dynamic_frame,
            text="Normalizza descrizione processo (AI)",
            fg_color="#444",
            command=lambda: self._normalize_process_ai(mat),
        ).pack(fill="x", pady=4)

        ctk.CTkButton(
            self.dynamic_frame,
            text="Applica a materiale",
            fg_color=COLOR_ACCENT,
            command=lambda: self._apply_material_inspector(mat, prov, at_var, tags_e, pd),
        ).pack(fill="x", pady=8)

    def _inspector_widgets(self):
        if not hasattr(self, "_inspector_refs"):
            self._inspector_refs = {}

    def _inspector_field(self, key, widget):
        self._inspector_widgets()
        self._inspector_refs[key] = widget

    def _normalize_process_ai(self, mat):
        if not self.importer:
            return
        pd = self._inspector_refs.get("process_desc")
        if not pd:
            return
        text = pd.get("1.0", "end").strip()
        if not text:
            return
        parsed = self.importer.process_parser.parse(text, output_name="")
        pd.delete("1.0", "end")
        pd.insert("1.0", json.dumps(parsed, indent=2, ensure_ascii=False))

    def _apply_material_inspector(self, mat, prov, at_var, tags_e, pd):
        scope = self.selection.get("scope")
        tgt = self.staging_project if scope == "staging" else self.project_materials
        if mat not in tgt:
            return
        blob = tgt[mat]
        blob["provider"] = prov.get().strip() or "UnknownProvider"
        blob["asset_type"] = at_var.get()
        blob["tags"] = [t.strip() for t in tags_e.get().split(",") if t.strip()]
        blob["process_description"] = pd.get("1.0", "end").strip()
        for fd in blob.get("folders", {}).values():
            fd["is_custom"] = blob["asset_type"] == "CUSTOM"
        self.refresh_staging_ui() if scope == "staging" else self.refresh_builder_ui()

    def _render_inspector_variant(self, scope, mat, variant):
        for w in self.dynamic_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self.dynamic_frame,
            text=f"{mat} / {variant}",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")
        blob = self._material_blob(scope, mat)
        vdata = blob.get("folders", {}).get(variant, {})
        ctk.CTkLabel(
            self.dynamic_frame,
            text=f"Tag: {', '.join(vdata.get('variant_tags', [])) or '—'}",
            font=("Segoe UI", 11),
        ).pack(anchor="w")

    def _render_inspector_file(self, scope, mat, variant, file_obj):
        for w in self.dynamic_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self.dynamic_frame, text=file_obj.get("name", ""), font=("Segoe UI", 12, "bold")).pack(
            anchor="w"
        )
        rows = [
            ("map_type", file_obj.get("map_type")),
            ("tech_res", file_obj.get("tech_res")),
            ("visual", f"{file_obj.get('visual_validation')} ({file_obj.get('visual_confidence', 0):.2f})"),
            ("naming conf", f"{file_obj.get('naming_confidence', 0):.2f}"),
            ("AI", file_obj.get("ai_description") or "—"),
        ]
        for k, v in rows:
            ctk.CTkLabel(self.dynamic_frame, text=f"{k}: {v}", font=("Segoe UI", 10)).pack(anchor="w")

        src = ctk.CTkEntry(self.dynamic_frame, placeholder_text="Source RAW (filename o path)")
        src.insert(0, file_obj.get("source_raw", "") or ", ".join(file_obj.get("derived_from", [])))
        src.pack(fill="x", pady=6)
        self._inspector_field("source_raw", src)

        def save_src():
            file_obj["source_raw"] = src.get().strip()
            messagebox.showinfo("Inspector", "Source RAW aggiornato (in memoria).")

        ctk.CTkButton(self.dynamic_frame, text="Salva Source RAW", command=save_src).pack(fill="x")

    # --- Auto-sort fuzzy ---
    def execute_auto_sort(self):
        for mat, data in list(self.staging_project.items()):
            target = self._find_best_material_match(mat)
            if target is None:
                target = mat
                self.project_materials[target] = {
                    "provider": data.get("provider", "Auto"),
                    "asset_type": data.get("asset_type", "RAW"),
                    "tags": data.get("tags", []),
                    "desc": data.get("desc", ""),
                    "process_description": data.get("process_description", ""),
                    "relationships": data.get("relationships", []),
                    "folders": {},
                }

            vault = self.project_materials[target]
            for vname, vdata in data.get("folders", {}).items():
                dest_key = self._match_vault_variant(vault, vname)
                slot = vault["folders"].setdefault(
                    dest_key,
                    {
                        "is_custom": vdata.get("is_custom", False),
                        "variant_tags": vdata.get("variant_tags", []),
                        "files": [],
                    },
                )
                seen = {f"{f.get('name', '')}|{f.get('tech_res', '')}" for f in slot["files"]}
                for f in vdata.get("files", []):
                    key = f"{f.get('name', '')}|{f.get('tech_res', '')}"
                    if key in seen:
                        continue
                    slot["files"].append(f)
                    seen.add(key)

            del self.staging_project[mat]

        self.auto_sort_btn.pack_forget()
        self.refresh_builder_ui()
        self.refresh_staging_ui()

    def _match_vault_variant(self, vault_mat: dict, incoming_variant: str) -> str:
        folders = vault_mat.get("folders", {})
        if incoming_variant in folders:
            return incoming_variant
        inc_norm = incoming_variant.replace("-", "_").upper()
        for k in folders:
            if k.replace("-", "_").upper() == inc_norm:
                return k
        return incoming_variant

    def _find_best_material_match(self, incoming_name: str):
        if not self.project_materials:
            return None
        incoming_norm = self._normalize_material_name(incoming_name)
        best = (None, 0.0)
        for candidate in self.project_materials:
            cand_norm = self._normalize_material_name(candidate)
            score = SequenceMatcher(None, incoming_norm, cand_norm).ratio()
            if incoming_norm in cand_norm or cand_norm in incoming_norm:
                score = max(score, 0.92)
            if score > best[1]:
                best = (candidate, score)
        return best[0] if best[1] >= 0.84 else None

    @staticmethod
    def _normalize_material_name(name: str) -> str:
        tokens = [t for t in re.split(r"[_\-\s\.]+", name.lower()) if t]
        noisy = {"1k", "2k", "4k", "8k", "16k", "png", "jpg", "jpeg", "tif", "tga", "exr"}
        return "_".join([t for t in tokens if t not in noisy])


if __name__ == "__main__":
    app = SignumSentinelGUI()
    app.mainloop()
