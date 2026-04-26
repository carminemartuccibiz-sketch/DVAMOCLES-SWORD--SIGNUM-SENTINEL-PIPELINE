import os, json, gc, threading, tkinter as tk, customtkinter as ctk, psutil
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path
from utils.runtime_paths import get_app_root, resolve_resource

# --- TENTATIVO IMPORTAZIONE MODULI CORE ---
try:
    from core.import_assistant import AdvancedImporter
    from core.api_fetcher import AmbientCGFetcher
    from core.pipeline_orchestrator import PipelineOrchestrator
    from core.provider_knowledge import PhysicallyBasedKnowledgeFetcher

    HAS_BACKEND = True
except ImportError:
    HAS_BACKEND = False

# --- GESTIONE HARDWARE TELEMETRY ---
try:
    import GPUtil
except:
    GPUtil = None

# --- GESTIONE DRAG & DROP ---
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES

    HAS_DND = True
except ImportError:
    HAS_DND = False

# --- DEFINIZIONE CLASSE CON EREDITARIETÀ INCROCIATA ---
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
        super().__init__()
        self.app_root = get_app_root()

        self.title("DVAMOCLES SWORD™ | MASTER DATA FORGE")
        self.geometry("1800x950")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self._set_window_icon()

        # Inizializzazione Backend
        self.importer = AdvancedImporter(self.app_root) if HAS_BACKEND else None
        self.orchestrator = PipelineOrchestrator(self.app_root, self.importer) if self.importer else None
        self.web_fetcher = AmbientCGFetcher(self.app_root) if HAS_BACKEND else None
        self.pb_fetcher = PhysicallyBasedKnowledgeFetcher(self.app_root) if HAS_BACKEND else None

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
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _set_window_icon(self):
        icon_candidates = []
        env_icon = os.environ.get("SIGNUM_ICON")
        if env_icon:
            icon_candidates.append(Path(env_icon))
        icon_candidates.append(resolve_resource("signum_icon.ico"))
        for icon_path in icon_candidates:
            try:
                if icon_path.exists():
                    self.iconbitmap(str(icon_path))
                    return
            except Exception:
                continue

    def _load_state(self):
        p = self.app_root / "config" / "gui_state.json"
        if p.exists():
            try:
                with open(p, "r") as f:
                    return json.load(f)
            except:
                pass
        return {}

    def _save_state(self):
        cfg_dir = self.app_root / "config"
        os.makedirs(cfg_dir, exist_ok=True)
        with open(cfg_dir / "gui_state.json", "w") as f:
            json.dump(self.tree_state, f)

    def on_closing(self):
        if messagebox.askokcancel("Esci", "Vuoi chiudere DVAMOCLES SWORD e liberare la VRAM?"):
            if self.importer:
                self.importer.unload_ai()
            self._save_state()
            self.destroy()

    def setup_telemetry_bar(self):
        self.telemetry_frame = ctk.CTkFrame(self, height=30, corner_radius=0, fg_color="#0a0a0a")
        self.telemetry_frame.pack(fill="x", side="top")

        self.lbl_cpu = ctk.CTkLabel(self.telemetry_frame, text="CPU: 0% | RAM: 0%", font=("Courier", 12))
        self.lbl_cpu.pack(side="left", padx=20)

        self.ai_btn = ctk.CTkButton(self.telemetry_frame, text="IA: OFF", width=60, fg_color="#333", command=self.toggle_ai)
        self.ai_btn.pack(side="right", padx=10)

    def toggle_ai(self):
        if not self.importer:
            return
        if self.importer.ai_model is None:
            self.importer.load_ai()
            self.ai_btn.configure(text="IA: ON", fg_color="#6200ea")
        else:
            self.importer.unload_ai()
            self.ai_btn.configure(text="IA: OFF", fg_color="#333")

    def update_telemetry(self):
        self.lbl_cpu.configure(text=f"CPU: {psutil.cpu_percent()}% | RAM: {psutil.virtual_memory().percent}%")
        self.after(2000, self.update_telemetry)

    # ==========================================
    # 1. ASSET BROWSER (STAGING)
    # ==========================================
    def setup_staging_panel(self):
        self.staging_frame = ctk.CTkFrame(self.main_container, fg_color="#121212")
        self.staging_frame.grid(row=0, column=0, sticky="nsew", padx=2)

        hdr = ctk.CTkFrame(self.staging_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=10)
        ctk.CTkLabel(hdr, text="1. ASSET BROWSER", font=("Arial", 14, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(hdr, text="Provider Info", width=110, command=self.fetch_provider_info).pack(side="right", padx=5)
        ctk.CTkButton(hdr, text="Catalog 20", width=90, command=self.fetch_provider_catalog_page).pack(side="right", padx=5)
        ctk.CTkButton(hdr, text="☁ Fetch Web", width=100, command=self.fetch_from_web).pack(side="right", padx=5)
        ctk.CTkButton(hdr, text="AmbientCG ALL", width=110, command=self.import_ambientcg_all).pack(side="right", padx=5)
        ctk.CTkButton(hdr, text="+ Folder", width=80, command=self.browse_folder).pack(side="right", padx=5)

        self.sort_container = ctk.CTkFrame(self.staging_frame, fg_color="transparent")
        self.sort_container.pack(fill="x", padx=10)
        self.auto_sort_btn = ctk.CTkButton(self.sort_container, text="✨ AI AUTO-SORT", fg_color="#6200ea", command=self.execute_auto_sort)

        self.stage_scroll = ctk.CTkScrollableFrame(self.staging_frame, fg_color="#1e1e1e")
        self.stage_scroll.pack(fill="both", expand=True, padx=5, pady=5)

        if HAS_DND:
            try:
                self.drop_target_register(DND_FILES)
                self.dnd_bind("<<Drop>>", self.on_drop)
            except:
                pass

    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self._process_paths([folder])

    def fetch_from_web(self):
        if not self.web_fetcher or not self.importer:
            return
        asset_id = simpledialog.askstring("Fetch from Web", "Asset ID ambientCG (es: Rock035):", parent=self)
        if not asset_id:
            return
        self._download_with_progress(asset_id=asset_id)

    def _download_with_progress(self, asset_id: str):
        win = ctk.CTkToplevel(self)
        win.title("Download Provider")
        win.geometry("420x130")
        win.resizable(False, False)
        status = ctk.CTkLabel(win, text=f"Downloading all variants for {asset_id}...")
        status.pack(pady=(14, 8))
        bar = ctk.CTkProgressBar(win)
        bar.pack(fill="x", padx=16, pady=8)
        bar.set(0.0)
        bytes_lbl = ctk.CTkLabel(win, text="0 / 0 variants")
        bytes_lbl.pack(pady=(0, 8))
        done = {"ok": False, "path": None, "error": "", "variants": 0}

        def progress_cb(done_count: int, total_count: int):
            def _ui():
                if total_count > 0:
                    bar.set(min(1.0, done_count / total_count))
                    bytes_lbl.configure(text=f"{done_count} / {total_count} variants")
                else:
                    bytes_lbl.configure(text=f"{done_count} variants")
            self.after(0, _ui)

        def worker():
            try:
                staging_dir = self.app_root / "temp" / "staging_web" / asset_id
                extracted = self.web_fetcher.download_all_variants(
                    asset_id=asset_id,
                    dest_folder=staging_dir,
                    progress_cb=progress_cb,
                )
                done["ok"] = True
                done["path"] = str(extracted.get("root_path", ""))
                done["variants"] = len(extracted.get("variants", []))
            except Exception as exc:
                done["error"] = str(exc)
            finally:
                self.after(0, finalize)

        def finalize():
            if win.winfo_exists():
                win.destroy()
            if done["ok"] and done["path"]:
                self._process_paths([done["path"]])
                messagebox.showinfo("Fetch Complete", f"Asset scaricato (tutte le varianti): {done['variants']}\n{done['path']}")
            else:
                messagebox.showerror("Fetch Error", done["error"] or "Unknown error")

        threading.Thread(target=worker, daemon=True).start()

    def fetch_provider_catalog_page(self):
        if not self.web_fetcher:
            return
        query = simpledialog.askstring("Catalog Fetch", "Query (opzionale):", parent=self) or ""
        page_str = simpledialog.askstring("Catalog Fetch", "Page number (20 per page):", parent=self) or "1"
        try:
            page = max(1, int(page_str))
            out = self.web_fetcher.export_catalog_page(query=query, page=page, page_size=20)
            messagebox.showinfo("Catalog Saved", f"Catalogo salvato:\n{out}")
        except Exception as exc:
            messagebox.showerror("Catalog Error", str(exc))

    def fetch_provider_info(self):
        provider = simpledialog.askstring("Provider Info", "Provider info source (ambientcg/physicallybased):", parent=self) or "ambientcg"
        provider = provider.strip().lower()
        if provider == "ambientcg":
            try:
                out_dir = self.app_root / "06_KNOWLEDGE_BASE" / "sources" / "api"
                out_dir.mkdir(parents=True, exist_ok=True)
                mode = simpledialog.askstring(
                    "Provider Info",
                    "Mode (asset/categories/collections/rss):",
                    parent=self,
                ) or "asset"
                mode = mode.strip().lower()
                if mode == "asset":
                    asset_id = simpledialog.askstring("Provider Info", "Asset ID ambientCG:", parent=self)
                    if not asset_id:
                        return
                    payload = self.web_fetcher.get_asset_metadata(asset_id)
                    out_path = out_dir / f"ambientcg_asset_{asset_id}.json"
                    with open(out_path, "w", encoding="utf-8") as fh:
                        json.dump(payload, fh, indent=2, ensure_ascii=False)
                elif mode == "categories":
                    payload = self.web_fetcher.fetch_categories()
                    out_path = out_dir / "ambientcg_categories.json"
                    with open(out_path, "w", encoding="utf-8") as fh:
                        json.dump(payload, fh, indent=2, ensure_ascii=False)
                elif mode == "collections":
                    payload = self.web_fetcher.fetch_collections()
                    out_path = out_dir / "ambientcg_collections.json"
                    with open(out_path, "w", encoding="utf-8") as fh:
                        json.dump(payload, fh, indent=2, ensure_ascii=False)
                elif mode == "rss":
                    payload = self.web_fetcher.fetch_rss()
                    out_path = out_dir / "ambientcg_rss.xml"
                    with open(out_path, "w", encoding="utf-8") as fh:
                        fh.write(payload)
                else:
                    messagebox.showwarning("Provider Info", f"Mode non supportata: {mode}")
                    return
                messagebox.showinfo("Provider Info", f"Dati salvati:\n{out_path}")
            except Exception as exc:
                messagebox.showerror("Provider Info Error", str(exc))
            return
        if provider == "physicallybased":
            if not self.pb_fetcher:
                return
            repo_url = simpledialog.askstring(
                "Provider Info",
                "Git repository URL (ENTER = default physically-based-api):",
                parent=self,
            ) or ""
            blob_url = simpledialog.askstring(
                "Provider Info",
                "Blob URL opzionale (es: blob:https://physicallybased.info/...)",
                parent=self,
            ) or ""
            try:
                rep = self.pb_fetcher.ingest_from_github_repository(repo_url=repo_url)
                messagebox.showinfo(
                    "PhysicallyBased Imported",
                    (
                        f"Materials: {rep['materials']}\n"
                        f"Lights: {rep['light_sources']}\n"
                        f"Cameras: {rep['cameras']}\n"
                        f"Lenses: {rep['lenses']}\n"
                        f"MaterialX links: {rep.get('materialx_links', 0)}\n"
                        f"Output: {rep['output_path']}"
                    ),
                )
            except Exception as exc:
                messagebox.showerror("PhysicallyBased Error", str(exc))
            return
        messagebox.showwarning(
            "Provider non pronto",
            f"Provider '{provider}' predisposto per futuro API/crawling.\nAttualmente supportati: ambientcg, physicallybased.",
        )

    def import_ambientcg_all(self):
        if not self.web_fetcher:
            return
        batch_str = simpledialog.askstring("AmbientCG ALL", "Batch size (20-30 consigliato):", parent=self) or "20"
        try:
            batch_size = max(1, int(batch_str))
        except ValueError:
            messagebox.showerror("Input Error", "Batch size non valido.")
            return

        win = ctk.CTkToplevel(self)
        win.title("AmbientCG Bulk Import")
        win.geometry("500x150")
        status = ctk.CTkLabel(win, text="Preparazione catalogo...")
        status.pack(pady=(14, 8))
        bar = ctk.CTkProgressBar(win)
        bar.pack(fill="x", padx=16, pady=8)
        bar.set(0.0)
        detail = ctk.CTkLabel(win, text="0 / 0")
        detail.pack(pady=(0, 8))
        done = {"ok": False, "error": "", "paths": [], "count": 0}
        resume_state = self.web_fetcher.load_bulk_resume_state()
        use_resume = False
        if resume_state.get("in_progress"):
            use_resume = messagebox.askyesno(
                "Resume Batch",
                (
                    "Trovato stato batch precedente.\n"
                    f"Offset: {resume_state.get('next_offset', 0)}\n"
                    f"Completati: {len(resume_state.get('completed_ids', []))}\n\n"
                    "Vuoi riprendere da questo punto?"
                ),
            )

        def worker():
            try:
                next_offset = int(resume_state.get("next_offset", 0)) if use_resume else 0
                completed_ids = set(resume_state.get("completed_ids", [])) if use_resume else set()
                first = self.web_fetcher.list_assets_offset(query="", limit=batch_size, offset=next_offset)
                total = int(first.get("total_results", 0))
                downloaded = int(resume_state.get("downloaded", 0)) if use_resume else 0
                extracted_paths = []
                offset = next_offset
                page_payload = first
                while True:
                    assets = page_payload.get("assets", [])
                    if not assets:
                        break
                    for item in assets:
                        asset_id = str(item.get("id", "")).strip()
                        if not asset_id or asset_id in completed_ids:
                            continue
                        try:
                            staging_dir = self.app_root / "temp" / "staging_web" / asset_id
                            extracted = self.web_fetcher.download_all_variants(
                                asset_id=asset_id,
                                dest_folder=staging_dir,
                            )
                            root_path = str(extracted.get("root_path", ""))
                            if root_path:
                                extracted_paths.append(root_path)
                        except Exception:
                            pass
                        completed_ids.add(asset_id)
                        downloaded += 1
                        self.web_fetcher.save_bulk_resume_state(
                            {
                                "in_progress": True,
                                "batch_size": batch_size,
                                "next_offset": offset,
                                "downloaded": downloaded,
                                "completed_ids": sorted(completed_ids),
                            }
                        )
                        self.after(
                            0,
                            lambda d=downloaded, t=max(1, total): (
                                bar.set(d / t),
                                detail.configure(text=f"{d} / {t}"),
                            ),
                        )
                    offset += batch_size
                    if offset >= total:
                        break
                    page_payload = self.web_fetcher.list_assets_offset(query="", limit=batch_size, offset=offset)
                done["ok"] = True
                done["paths"] = extracted_paths
                done["count"] = len(extracted_paths)
                self.web_fetcher.clear_bulk_resume_state()
            except Exception as exc:
                done["error"] = str(exc)
                self.web_fetcher.save_bulk_resume_state(
                    {
                        "in_progress": True,
                        "batch_size": batch_size,
                        "next_offset": int(resume_state.get("next_offset", 0)) if use_resume else 0,
                        "downloaded": 0,
                        "completed_ids": [],
                    }
                )
            finally:
                self.after(0, finalize)

        def finalize():
            if win.winfo_exists():
                win.destroy()
            if done["ok"]:
                if done["paths"]:
                    self._process_paths(done["paths"])
                messagebox.showinfo("AmbientCG Import", f"Asset estratti: {done['count']}")
            else:
                messagebox.showerror("AmbientCG Import Error", done["error"] or "Unknown error")

        threading.Thread(target=worker, daemon=True).start()

    def on_drop(self, event):
        import re

        paths = [p.strip("{}") for p in re.findall(r"\{.*?\}|\S+", event.data)]
        self._process_paths(paths)

    def _process_paths(self, paths):
        if not self.importer:
            return
        staged_project = self.importer.ingest_paths(paths, max_depth=4)
        for material_name, payload in staged_project.items():
            folder_files = []
            for variant_payload in payload.get("folders", {}).values():
                folder_files.extend(variant_payload.get("files", []))
            if folder_files:
                self.staged_groups[material_name] = folder_files

        if self.staged_groups:
            self.auto_sort_btn.pack(fill="x", pady=5)
        self.refresh_staging_ui()

    def refresh_staging_ui(self):
        for w in self.stage_scroll.winfo_children():
            w.destroy()
        for group, files in self.staged_groups.items():
            g_frame = ctk.CTkFrame(self.stage_scroll, fg_color="#2c2c2c")
            g_frame.pack(fill="x", pady=2, padx=2)
            ctk.CTkLabel(g_frame, text=f"📁 {group}", font=("Arial", 12, "bold")).pack(anchor="w", padx=10)

            for i, f in enumerate(files):
                f_frame = ctk.CTkFrame(g_frame, fg_color="#1a1a1a")
                f_frame.pack(fill="x", pady=1, padx=5)

                meta = f"[{f.get('map_type')} | {f.get('tech_res')}]"
                lbl = ctk.CTkLabel(f_frame, text=f"📄 {f['name']} {meta}", font=("Arial", 11), cursor="hand2")
                lbl.pack(side="left", padx=5)

                # Permette di editare il file in staging
                file_id = f"staging|{group}|{i}"
                lbl.bind("<Button-1>", lambda e, id_s=file_id: self.set_inspector("staged_file", id_s))

    def execute_auto_sort(self):
        for group, files in self.staged_groups.items():
            # Fuzzy match logica (Nesting automatico)
            if group not in self.project_materials:
                self.project_materials[group] = {
                    "provider": "Unknown",
                    "technique": "",
                    "tags": [],
                    "folders": {"Root": {"is_custom": False, "format": "Auto", "resolution": "Auto", "auto_generate_maps": True, "files": files}},
                }
            else:
                if "Root" not in self.project_materials[group]["folders"]:
                    self.project_materials[group]["folders"]["Root"] = {
                        "is_custom": False,
                        "format": "Auto",
                        "resolution": "Auto",
                        "auto_generate_maps": True,
                        "files": [],
                    }
                self.project_materials[group]["folders"]["Root"]["files"].extend(files)

        self.staged_groups = {}
        self.auto_sort_btn.pack_forget()
        self.refresh_builder_ui()
        self.refresh_staging_ui()

    # ==========================================
    # 2. PROJECT VAULT (TREE HIERARCHY)
    # ==========================================
    def setup_builder_panel(self):
        self.builder_frame = ctk.CTkFrame(self.main_container, fg_color="#161b22")
        self.builder_frame.grid(row=0, column=1, sticky="nsew", padx=2)
        hdr = ctk.CTkFrame(self.builder_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=8, padx=6)
        ctk.CTkLabel(hdr, text="2. PROJECT VAULT", font=("Arial", 14, "bold")).pack(side="left", padx=4)
        ctk.CTkButton(hdr, text="+ Material", width=90, command=self.create_material_manual).pack(side="right", padx=4)
        ctk.CTkButton(hdr, text="+ Folder", width=80, command=self.create_folder_manual).pack(side="right", padx=4)
        ctk.CTkButton(hdr, text="+ File", width=70, command=self.add_file_manual).pack(side="right", padx=4)
        self.builder_scroll = ctk.CTkScrollableFrame(self.builder_frame, fg_color="#0d1117")
        self.builder_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        self.refresh_builder_ui()

    def create_material_manual(self):
        name = simpledialog.askstring("Nuovo Materiale", "Nome materiale:", parent=self)
        if not name:
            return
        mat_name = name.strip()
        if not mat_name:
            return
        if mat_name in self.project_materials:
            messagebox.showwarning("Materiale esistente", f"Il materiale '{mat_name}' esiste già.")
            return
        self.project_materials[mat_name] = {
            "provider": "Manual",
            "technique": "",
            "tags": [],
            "desc": "",
            "asset_type": "RAW",
            "folders": {
                "Root": {
                    "is_custom": False,
                    "format": "Auto",
                    "resolution": "Auto",
                    "auto_generate_maps": True,
                    "files": [],
                    "variant_tags": [],
                }
            },
        }
        self.active_selection = {"type": "material", "id": mat_name}
        self.refresh_builder_ui()
        self.refresh_inspector_ui()

    def create_folder_manual(self):
        if not self.project_materials:
            messagebox.showwarning("Project Vault", "Crea prima un materiale.")
            return
        mat_name = simpledialog.askstring("Nuova Cartella", "Materiale di destinazione:", parent=self)
        if not mat_name or mat_name.strip() not in self.project_materials:
            messagebox.showwarning("Project Vault", "Materiale non valido.")
            return
        mat_name = mat_name.strip()
        folder_name = simpledialog.askstring("Nuova Cartella", "Nome folder/texture-set:", parent=self)
        if not folder_name:
            return
        folder_name = folder_name.strip()
        if not folder_name:
            return
        folders = self.project_materials[mat_name].setdefault("folders", {})
        if folder_name in folders:
            messagebox.showwarning("Folder esistente", f"Folder '{folder_name}' già presente.")
            return
        folders[folder_name] = {
            "is_custom": False,
            "format": "Auto",
            "resolution": "Auto",
            "auto_generate_maps": True,
            "files": [],
            "variant_tags": [],
        }
        self.active_selection = {"type": "folder", "id": f"{mat_name}|{folder_name}"}
        self.refresh_builder_ui()
        self.refresh_inspector_ui()

    def add_file_manual(self):
        if not self.project_materials:
            messagebox.showwarning("Project Vault", "Crea prima materiale e folder.")
            return
        mat_name = simpledialog.askstring("Aggiungi File", "Materiale di destinazione:", parent=self)
        if not mat_name or mat_name.strip() not in self.project_materials:
            messagebox.showwarning("Project Vault", "Materiale non valido.")
            return
        mat_name = mat_name.strip()
        folders = self.project_materials[mat_name].get("folders", {})
        if not folders:
            messagebox.showwarning("Project Vault", "Il materiale non ha folder. Crea prima una folder.")
            return
        folder_name = simpledialog.askstring("Aggiungi File", "Folder di destinazione:", parent=self)
        if not folder_name or folder_name.strip() not in folders:
            messagebox.showwarning("Project Vault", "Folder non valida.")
            return
        folder_name = folder_name.strip()

        paths = filedialog.askopenfilenames(
            title="Seleziona file texture",
            filetypes=[
                ("Texture files", "*.png *.jpg *.jpeg *.tif *.tiff *.exr *.tga *.mtlx *.materialx"),
                ("All files", "*.*"),
            ],
        )
        if not paths:
            return
        for p_str in paths:
            p = Path(p_str)
            if not p.exists() or not p.is_file():
                continue
            rec = self.importer.auto_detect_file(str(p), provider=self.project_materials[mat_name].get("provider", "Manual")) if self.importer else {
                "name": p.name,
                "path": str(p),
                "map_type": "unknown",
                "format": p.suffix.replace(".", "").upper(),
                "resolution": "UNKNOWN",
                "tech_res": "Unknown",
                "bit_depth": "Unknown",
                "color_space": "Unknown",
                "is_custom": False,
                "derived_from": [],
                "source_raw": "",
                "process": "",
                "tool": "",
                "ai_description": "",
                "description_merged": "",
                "description_sources": [],
                "visual_validation": "Unknown",
                "visual_confidence": 0.0,
                "metadata_confidence": 0.0,
            }
            folders[folder_name].setdefault("files", []).append(rec)
        self.active_selection = {"type": "folder", "id": f"{mat_name}|{folder_name}"}
        self.refresh_builder_ui()
        self.refresh_inspector_ui()

    def toggle_tree(self, id_str):
        self.tree_state[id_str] = not self.tree_state.get(id_str, False)
        self._save_state()
        self.refresh_builder_ui()

    def refresh_builder_ui(self):
        for w in self.builder_scroll.winfo_children():
            w.destroy()
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

            self.drop_targets_geometry.append({"widget": m_frame, "id": ("material", mat_name, None)})

            if not is_open:
                continue

            for folder_name, folder_data in mat_data.get("folders", {}).items():
                v_frame = ctk.CTkFrame(m_frame, fg_color="#1a1a1a")
                v_frame.pack(fill="x", padx=10, pady=2)

                f_hdr = ctk.CTkFrame(v_frame, fg_color="transparent")
                f_hdr.pack(fill="x")

                fid = f"{mat_name}|{folder_name}"
                f_is_open = self.tree_state.get(fid, True)
                ctk.CTkButton(f_hdr, text="▼" if f_is_open else "▶", width=20, fg_color="transparent", command=lambda i=fid: self.toggle_tree(i)).pack(side="left")

                c_color = "#ff8a80" if folder_data.get("is_custom") else "#00b0ff"
                f_lbl = ctk.CTkLabel(f_hdr, text=f"📂 {folder_name}", font=("Arial", 12, "bold"), text_color=c_color, cursor="hand2")
                f_lbl.pack(side="left", padx=5, pady=2)
                f_lbl.bind("<Button-1>", lambda e, id_s=fid: self.set_inspector("folder", id_s))

                if not f_is_open:
                    continue

                for i, f_obj in enumerate(folder_data.get("files", [])):
                    file_id = f"{mat_name}|{folder_name}|{i}"
                    fi_f = ctk.CTkFrame(v_frame, fg_color="transparent")
                    fi_f.pack(fill="x")

                    file_color = "#ff8a80" if f_obj.get("is_custom") else "#aaaaaa"
                    real_name = Path(f_obj.get("path", f_obj.get("name", "Unknown"))).name
                    fmt_res = f"[{f_obj.get('map_type')} | {f_obj.get('tech_res')}]"
                    lbl = ctk.CTkLabel(fi_f, text=f"   ↳ 📄 {real_name} {fmt_res}", text_color=file_color, cursor="hand2")
                    lbl.pack(side="left", padx=5)
                    lbl.bind("<Button-1>", lambda e, id_s=file_id: self.set_inspector("file", id_s))

    # ==========================================
    # 3. METADATA INSPECTOR (EDITING & FORGE)
    # ==========================================
    def setup_inspector_panel(self):
        self.inspector_frame = ctk.CTkFrame(self.main_container, fg_color="#121212")
        self.inspector_frame.grid(row=0, column=2, sticky="nsew", padx=2)

        self.ins_header = ctk.CTkLabel(self.inspector_frame, text="3. INSPECTOR", font=("Arial", 14, "bold"))
        self.ins_header.pack(pady=10)

        self.dynamic_frame = ctk.CTkScrollableFrame(self.inspector_frame, fg_color="transparent")
        self.dynamic_frame.pack(fill="both", expand=True, padx=10)

        # IL TASTO FORGE
        self.import_btn = ctk.CTkButton(self.inspector_frame, text="EXECUTE FORGE", fg_color="#d32f2f", height=40, font=("Arial", 16, "bold"), command=self.start_forge)
        self.import_btn.pack(side="bottom", fill="x", padx=20, pady=20)

    def set_inspector(self, type_, id_str):
        self.active_selection = {"type": type_, "id": id_str}
        self.refresh_inspector_ui()

    def refresh_inspector_ui(self):
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()
        stype = self.active_selection.get("type")
        sid = self.active_selection.get("id")
        if not stype:
            return

        ui_prefs = self.importer.ui_prefs if self.importer else {"providers": [], "formats": [], "resolutions": [], "map_types": []}

        if stype == "material":
            mat = self.project_materials[sid]
            self.ins_header.configure(text=f"MATERIAL: {sid}")

            ctk.CTkLabel(self.dynamic_frame, text="Material Name:").pack(anchor="w")
            self.p_name = ctk.CTkEntry(self.dynamic_frame)
            self.p_name.insert(0, sid)
            self.p_name.pack(fill="x", pady=2)

            ctk.CTkLabel(self.dynamic_frame, text="Provider:").pack(anchor="w")
            self.p_prov = ctk.CTkComboBox(self.dynamic_frame, values=ui_prefs.get("providers", ["Generic", "AmbientCG", "Quixel"]))
            self.p_prov.set(mat.get("provider", "Generic"))
            self.p_prov.pack(fill="x", pady=2)

            ctk.CTkLabel(self.dynamic_frame, text="Technique:").pack(anchor="w")
            self.p_tech = ctk.CTkComboBox(self.dynamic_frame, values=["Photogrammetry", "Procedural", "AI Generated", "Scanned"])
            self.p_tech.set(mat.get("technique", ""))
            self.p_tech.pack(fill="x", pady=2)

            ctk.CTkLabel(self.dynamic_frame, text="Tags (comma separated):").pack(anchor="w")
            self.p_tags = ctk.CTkEntry(self.dynamic_frame)
            self.p_tags.insert(0, ", ".join(mat.get("tags", [])))
            self.p_tags.pack(fill="x", pady=2)

            ctk.CTkButton(self.dynamic_frame, text="Save Material", command=lambda: self._save_mat(sid)).pack(pady=15)

        elif stype == "folder":
            mat_name, f_name = sid.split("|")
            folder = self.project_materials[mat_name]["folders"][f_name]
            self.ins_header.configure(text=f"TEXTURE SET: {f_name}")

            ctk.CTkLabel(self.dynamic_frame, text="Set Name:").pack(anchor="w")
            self.f_name_entry = ctk.CTkEntry(self.dynamic_frame)
            self.f_name_entry.insert(0, f_name)
            self.f_name_entry.pack(fill="x", pady=2)

            # SWITCH RAW / CUSTOM SU FOLDER
            self.f_custom_var = ctk.BooleanVar(value=folder.get("is_custom", False))
            sw = ctk.CTkSwitch(
                self.dynamic_frame,
                text="IS CUSTOM (Generated/Modified)",
                variable=self.f_custom_var,
                command=lambda: self._save_folder(mat_name, f_name, True),
            )
            sw.pack(anchor="w", pady=10)

            if self.f_custom_var.get():
                ctk.CTkLabel(self.dynamic_frame, text="Process Workflow (Description):").pack(anchor="w")
                self.f_proc = ctk.CTkEntry(self.dynamic_frame)
                self.f_proc.insert(0, folder.get("process", ""))
                self.f_proc.pack(fill="x", pady=2)

            ctk.CTkLabel(self.dynamic_frame, text="Resolution Target:").pack(anchor="w", pady=(10, 0))
            self.f_res = ctk.CTkComboBox(self.dynamic_frame, values=["Auto", "1K", "2K", "4K", "8K"])
            self.f_res.set(folder.get("resolution", "Auto"))
            self.f_res.pack(fill="x", pady=2)

            ctk.CTkLabel(self.dynamic_frame, text="Set Tags (comma separated):").pack(anchor="w", pady=(10, 0))
            self.f_tags = ctk.CTkEntry(self.dynamic_frame)
            self.f_tags.insert(0, ", ".join(folder.get("variant_tags", [])))
            self.f_tags.pack(fill="x", pady=2)

            self.f_auto_gen_var = ctk.BooleanVar(value=folder.get("auto_generate_maps", False))
            ctk.CTkSwitch(
                self.dynamic_frame,
                text="AUTO GENERATE MISSING MAPS (NORMAL/ROUGH/AO/HEIGHT)",
                variable=self.f_auto_gen_var,
            ).pack(anchor="w", pady=8)

            ctk.CTkButton(self.dynamic_frame, text="Save Set", command=lambda: self._save_folder(mat_name, f_name)).pack(pady=15)

        elif stype in ["file", "staged_file"]:
            is_staged = stype == "staged_file"
            if is_staged:
                _, grp, idx_str = sid.split("|")
                f_idx = int(idx_str)
                f_obj = self.staged_groups[grp][f_idx]
            else:
                mat_name, f_name, f_idx_str = sid.split("|")
                f_idx = int(f_idx_str)
                f_obj = self.project_materials[mat_name]["folders"][f_name]["files"][f_idx]

            self.ins_header.configure(text=f"FILE: {Path(f_obj.get('path', f_obj.get('name', ''))).name}")

            ctk.CTkLabel(self.dynamic_frame, text="File Name:").pack(anchor="w")
            self.fi_name = ctk.CTkEntry(self.dynamic_frame)
            self.fi_name.insert(0, f_obj.get("name", ""))
            self.fi_name.pack(fill="x", pady=2)

            # SWITCH RAW / CUSTOM SU SINGOLO FILE
            self.fi_custom_var = ctk.BooleanVar(value=f_obj.get("is_custom", False))
            ctk.CTkSwitch(self.dynamic_frame, text="IS CUSTOM FILE", variable=self.fi_custom_var).pack(anchor="w", pady=5)

            ctk.CTkLabel(self.dynamic_frame, text="Map Type:").pack(anchor="w", pady=(10, 0))

            saved_map = f_obj.get("map_type", "Unknown").upper()
            display_map = "NORMAL" if saved_map.startswith("NORMAL") else saved_map

            self.fi_map = ctk.CTkComboBox(self.dynamic_frame, values=["ALBEDO", "NORMAL", "ROUGHNESS", "METALLIC", "AO", "HEIGHT", "UNKNOWN"])
            self.fi_map.set(display_map)
            self.fi_map.pack(fill="x", pady=2)

            ctk.CTkLabel(self.dynamic_frame, text="File Tags (comma separated):").pack(anchor="w", pady=(10, 0))
            self.fi_tags = ctk.CTkEntry(self.dynamic_frame)
            self.fi_tags.insert(0, ", ".join(f_obj.get("tags", [])))
            self.fi_tags.pack(fill="x", pady=2)

            self.normal_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="transparent")
            ctk.CTkLabel(self.normal_frame, text="Normal Convention:").pack(anchor="w")
            self.fi_norm = ctk.CTkSegmentedButton(self.normal_frame, values=["DirectX", "OpenGL"])
            self.fi_norm.set("DirectX" if saved_map == "NORMAL_DX" else "OpenGL")

            if display_map == "NORMAL":
                self.normal_frame.pack(fill="x", pady=5)
            self.fi_map.configure(command=lambda c: self.normal_frame.pack(fill="x", pady=5) if c == "NORMAL" else self.normal_frame.pack_forget())

            # SIGNUM AI ANALYSIS BOX
            ai_frame = ctk.CTkFrame(self.dynamic_frame, fg_color="#1a1a1a")
            ai_frame.pack(fill="x", pady=10)
            ctk.CTkLabel(ai_frame, text="🧠 SIGNUM AI ANALYSIS", font=("Arial", 10, "bold"), text_color="#bb86fc").pack(anchor="w", padx=5)

            v_val = f_obj.get("visual_validation", "None")
            v_color = "#00e676" if v_val != "Unknown" else "#ff5252"
            ctk.CTkLabel(ai_frame, text=f"Pixel Type: {v_val}", text_color=v_color).pack(anchor="w", padx=10)

            ai_desc = f_obj.get("ai_description", "")
            if ai_desc:
                ctk.CTkLabel(ai_frame, text="AI Caption:", font=("Arial", 10, "italic")).pack(anchor="w", padx=10)
                desc_box = ctk.CTkTextbox(ai_frame, height=60, font=("Arial", 11))
                desc_box.insert("0.0", ai_desc)
                desc_box.configure(state="disabled")
                desc_box.pack(fill="x", padx=10, pady=5)

            cmd = (lambda: self._save_staged_file(grp, f_idx)) if is_staged else (lambda: self._save_file(mat_name, f_name, f_idx))
            ctk.CTkButton(self.dynamic_frame, text="Save File", command=cmd).pack(pady=15)

    # --- FUNZIONI DI SALVATAGGIO INSPECTOR ---
    def _save_mat(self, mat_name):
        new_name = self.p_name.get().strip() if hasattr(self, "p_name") else mat_name
        new_name = new_name or mat_name
        target = self.project_materials[mat_name]
        target["provider"] = self.p_prov.get()
        target["technique"] = self.p_tech.get()
        tags_raw = self.p_tags.get().strip() if hasattr(self, "p_tags") else ""
        target["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]
        if new_name != mat_name and new_name not in self.project_materials:
            self.project_materials[new_name] = target
            del self.project_materials[mat_name]
            self.active_selection = {"type": "material", "id": new_name}
        self.refresh_builder_ui()

    def _save_folder(self, mat_name, f_name, refresh_only=False):
        folder = self.project_materials[mat_name]["folders"][f_name]
        folder["is_custom"] = self.f_custom_var.get()
        if not refresh_only:
            if folder["is_custom"]:
                folder["process"] = self.f_proc.get().strip()
            folder["resolution"] = self.f_res.get()
            folder["auto_generate_maps"] = self.f_auto_gen_var.get()
            tags_raw = self.f_tags.get().strip() if hasattr(self, "f_tags") else ""
            folder["variant_tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]
            new_folder_name = self.f_name_entry.get().strip() if hasattr(self, "f_name_entry") else f_name
            if new_folder_name and new_folder_name != f_name:
                folders = self.project_materials[mat_name]["folders"]
                if new_folder_name not in folders:
                    folders[new_folder_name] = folder
                    del folders[f_name]
                    self.active_selection = {"type": "folder", "id": f"{mat_name}|{new_folder_name}"}
        self.refresh_builder_ui()
        if refresh_only:
            self.refresh_inspector_ui()

    def _save_file(self, mat_name, f_name, f_idx):
        f_obj = self.project_materials[mat_name]["folders"][f_name]["files"][f_idx]
        self._apply_file_save(f_obj)
        self.refresh_builder_ui()

    def _save_staged_file(self, grp, f_idx):
        f_obj = self.staged_groups[grp][f_idx]
        self._apply_file_save(f_obj)
        self.refresh_staging_ui()

    def _apply_file_save(self, f_obj):
        new_name = self.fi_name.get().strip() if hasattr(self, "fi_name") else ""
        if new_name:
            f_obj["name"] = new_name
            old_path = str(f_obj.get("path", ""))
            if old_path and not old_path.startswith(("http://", "https://", "mock://")):
                try:
                    f_obj["path"] = str(Path(old_path).with_name(new_name))
                except Exception:
                    pass
        f_obj["is_custom"] = self.fi_custom_var.get()
        new_map_type = self.fi_map.get().upper()
        if new_map_type == "NORMAL":
            conv = self.fi_norm.get()
            new_map_type = "NORMAL_DX" if conv == "DirectX" else "NORMAL_GL"
        f_obj["map_type"] = new_map_type
        tags_raw = self.fi_tags.get().strip() if hasattr(self, "fi_tags") else ""
        f_obj["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]

    def start_forge(self):
        """Lancia l'importazione definitiva."""
        if not HAS_BACKEND or not self.orchestrator:
            return
        res = self.orchestrator.run({"materials": self.project_materials})
        import_stage = res.get("stages", {}).get("import", {})
        done_materials = int(import_stage.get("processed_materials", 0))
        done_files = int(import_stage.get("processed_files", 0))
        skipped = int(import_stage.get("skipped_files", 0))
        dataset_stage = res.get("stages", {}).get("dataset_builder", {})
        segmented = int(res.get("stages", {}).get("segmentation", {}).get("masks_generated", 0))
        summary_msg = (
            f"Materiali: {done_materials}\n"
            f"File: {done_files}\n"
            f"Skipped: {skipped}\n"
            f"Maschere: {segmented}\n"
            f"Varianti dataset: {int(dataset_stage.get('total_variants', 0))}"
        )
        if res.get("status") in {"success", "partial_success"}:
            messagebox.showinfo("Forge Complete", summary_msg)
            self.project_materials = self.importer.load_existing_vault()
            self.staged_groups.clear()
            self.refresh_builder_ui()
            self.refresh_staging_ui()
        else:
            errors = res.get("stages", {}).get("ingestion", {}).get("errors", 0)
            messagebox.showerror("Forge Error", f"{summary_msg}\nErrors: {errors}")


if __name__ == "__main__":
    app = SignumSentinelGUI()
    app.mainloop()
