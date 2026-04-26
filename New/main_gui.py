import os
import json
import gc
import threading
import subprocess
import tkinter as tk
import customtkinter as ctk
import psutil
from tkinter import filedialog, messagebox, simpledialog
from pathlib import Path

from utils.runtime_paths import get_app_root, resolve_resource
from utils.logger_setup import init_session_logging

init_session_logging()

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

        self.title("DVAMOCLES SWORD™ | SIGNUM SENTINEL — Material Forge")
        self.geometry("1920x1000")
        self.minsize(1280, 720)
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
        self.ws: dict[str, ctk.CTkFrame] = {}
        self._ws_labels = (
            ("import", "Import"),
            ("vault", "Vault"),
            ("inspect", "Inspect"),
            ("ingest", "Ingest"),
            ("generate", "Generate"),
            ("dataset", "Dataset"),
            ("knowledge", "Knowledge"),
            ("pipeline", "Pipeline"),
        )
        self._label_to_ws = {lbl: key for key, lbl in self._ws_labels}

        self.setup_telemetry_bar()
        self.setup_workspace_bar()
        self.status_bar = ctk.CTkFrame(self, height=28, corner_radius=0, fg_color="#0d1117")
        self.status_bar.pack(side="bottom", fill="x")
        self.status_lbl = ctk.CTkLabel(
            self.status_bar,
            text="Pronto — seleziona un workspace",
            anchor="w",
            font=("Segoe UI", 11),
            text_color="#90a4ae",
        )
        self.status_lbl.pack(fill="x", padx=14, pady=4)
        self.workspace_host = ctk.CTkFrame(self, fg_color="#0a0a0a")
        self.workspace_host.pack(fill="both", expand=True)
        self.workspace_host.grid_rowconfigure(0, weight=1)
        self.workspace_host.grid_columnconfigure(0, weight=1)

        for key, _ in self._ws_labels:
            fr = ctk.CTkFrame(self.workspace_host, fg_color="transparent")
            fr.grid(row=0, column=0, sticky="nsew")
            fr.grid_remove()
            self.ws[key] = fr

        self.setup_staging_panel(self.ws["import"])
        self.setup_builder_panel(self.ws["vault"])
        self.setup_inspector_panel(self.ws["inspect"])
        self.setup_ingest_workspace(self.ws["ingest"])
        self.setup_generate_workspace(self.ws["generate"])
        self.setup_dataset_workspace(self.ws["dataset"])
        self.setup_knowledge_workspace(self.ws["knowledge"])
        self.setup_pipeline_workspace(self.ws["pipeline"])

        start_ws = self.tree_state.get("active_workspace", "import")
        if start_ws not in self.ws:
            start_ws = "import"
        self.show_workspace(start_ws, from_segment=False)

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

    def setup_workspace_bar(self):
        """Blender-style editor: one full-screen workspace per pipeline phase."""
        self.ws_bar = ctk.CTkFrame(self, height=48, corner_radius=0, fg_color="#141414")
        self.ws_bar.pack(fill="x", after=self.telemetry_frame)
        inner = ctk.CTkFrame(self.ws_bar, fg_color="transparent")
        inner.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(inner, text="Workspace", font=("Segoe UI", 11, "bold"), text_color="#888").pack(side="left", padx=(0, 10))
        labels = [lbl for _, lbl in self._ws_labels]
        self.ws_segment = ctk.CTkSegmentedButton(
            inner,
            values=labels,
            font=("Segoe UI", 12, "bold"),
            height=34,
            selected_color="#1565c0",
            selected_hover_color="#1976d2",
            command=self._on_workspace_segment,
        )
        self.ws_segment.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(inner, text="Ctrl+Tab: cycle", font=("Segoe UI", 10), text_color="#666").pack(side="right", padx=8)
        self.bind_all("<Control-Tab>", self._cycle_workspace_event)

    def _on_workspace_segment(self, label: str):
        key = self._label_to_ws.get(label, "import")
        self.show_workspace(key, from_segment=True)

    def _cycle_workspace_event(self, _event=None):
        keys = [k for k, _ in self._ws_labels]
        cur = self.tree_state.get("active_workspace", "import")
        try:
            i = keys.index(cur)
        except ValueError:
            i = 0
        nxt = keys[(i + 1) % len(keys)]
        self.show_workspace(nxt, from_segment=False)
        return "break"

    def show_workspace(self, key: str, *, from_segment: bool = False):
        if key not in self.ws:
            key = "import"
        for fr in self.ws.values():
            fr.grid_remove()
        self.ws[key].grid(row=0, column=0, sticky="nsew")
        self.tree_state["active_workspace"] = key
        self._save_state()
        rev = {k: v for k, v in self._ws_labels}
        if not from_segment:
            self.ws_segment.set(rev[key])
        if hasattr(self, "status_lbl"):
            tips = {
                "import": "Trascina cartelle o usa Fetch / Ambient bulk",
                "vault": "Gerarchia materiali e texture set",
                "inspect": "Modifica metadati e EXECUTE FORGE",
                "ingest": "Solo scansione vault → processed (senza import GUI)",
                "generate": "Derivazioni mappe e tool esterni",
                "dataset": "JSONL training e correlations",
                "knowledge": "API e file KB",
                "pipeline": "Tutta la catena post-import",
            }
            self.status_lbl.configure(text=f"{rev[key]} — {tips.get(key, '')}")

    # ==========================================
    # 1. ASSET BROWSER (STAGING) — workspace Import
    # ==========================================
    def setup_staging_panel(self, parent):
        self.staging_frame = ctk.CTkFrame(parent, fg_color="#121212")
        self.staging_frame.pack(fill="both", expand=True, padx=4, pady=4)

        hdr = ctk.CTkFrame(self.staging_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=10)
        ctk.CTkLabel(hdr, text="IMPORT — staging & provider download", font=("Segoe UI", 15, "bold")).pack(side="left", padx=10)
        ctk.CTkButton(hdr, text="+ Folder", width=90, command=self.browse_folder).pack(side="right", padx=4)
        ctk.CTkButton(hdr, text="AmbientCG ALL", width=120, command=self.import_ambientcg_all).pack(side="right", padx=4)
        ctk.CTkButton(hdr, text="Fetch Web", width=100, command=self.fetch_from_web).pack(side="right", padx=4)

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
    # 2. PROJECT VAULT — workspace Vault
    # ==========================================
    def setup_builder_panel(self, parent):
        self.builder_frame = ctk.CTkFrame(parent, fg_color="#161b22")
        self.builder_frame.pack(fill="both", expand=True, padx=4, pady=4)
        hdr = ctk.CTkFrame(self.builder_frame, fg_color="transparent")
        hdr.pack(fill="x", pady=8, padx=6)
        ctk.CTkLabel(hdr, text="VAULT — materiali, varianti, file", font=("Segoe UI", 15, "bold")).pack(side="left", padx=4)
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
    # 3. INSPECTOR + FORGE — workspace Inspect
    # ==========================================
    def setup_inspector_panel(self, parent):
        self.inspector_frame = ctk.CTkFrame(parent, fg_color="#121212")
        self.inspector_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.ins_header = ctk.CTkLabel(self.inspector_frame, text="INSPECT — proprietà & provenance", font=("Segoe UI", 15, "bold"))
        self.ins_header.pack(pady=10)

        self.dynamic_frame = ctk.CTkScrollableFrame(self.inspector_frame, fg_color="transparent")
        self.dynamic_frame.pack(fill="both", expand=True, padx=10)

        self.import_btn = ctk.CTkButton(
            self.inspector_frame,
            text="EXECUTE FORGE (import + pipeline)",
            fg_color="#c62828",
            hover_color="#e53935",
            height=44,
            font=("Segoe UI", 15, "bold"),
            command=self.start_forge,
        )
        self.import_btn.pack(side="bottom", fill="x", padx=20, pady=16)

    def setup_ingest_workspace(self, parent):
        root = ctk.CTkFrame(parent, fg_color="#0f1419")
        root.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(root, text="INGEST", font=("Segoe UI", 18, "bold")).pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(
            root,
            text="Scansione RAW/CUSTOM, manifest in 03_PROCESSED, metadati e quality gates interni all'ingestor.",
            font=("Segoe UI", 12),
            text_color="#9e9e9e",
            wraplength=920,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))
        row = ctk.CTkFrame(root, fg_color="transparent")
        row.pack(fill="x", pady=8)
        ctk.CTkButton(row, text="Run ingestion only", width=200, height=38, fg_color="#1565c0", command=self._run_ingest_only).pack(side="left", padx=(0, 12))
        ctk.CTkButton(row, text="Reload vault from disk", width=200, height=38, command=self._reload_vault).pack(side="left", padx=4)
        self.ingest_log = ctk.CTkTextbox(root, height=280, font=("Consolas", 11), wrap="word")
        self.ingest_log.pack(fill="both", expand=True, pady=12)

    def setup_generate_workspace(self, parent):
        root = ctk.CTkFrame(parent, fg_color="#0f1419")
        root.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(root, text="GENERATE", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            root,
            text="Mappe derivate (OpenCV), hook esterni (Materialize), packing ORM / ARM / RMA per correlazione training.",
            font=("Segoe UI", 12),
            text_color="#9e9e9e",
            wraplength=920,
            justify="left",
        ).pack(anchor="w", pady=(8, 16))
        ctk.CTkButton(root, text="Apri config external_generator.json", width=280, command=self._open_external_generator_config).pack(anchor="w", pady=4)
        ctk.CTkButton(root, text="Apri cartella 02_CUSTOM", width=220, command=lambda: self._open_path(self.app_root / "02_CUSTOM")).pack(anchor="w", pady=4)
        ctk.CTkButton(root, text="Apri cartella 03_PROCESSED", width=220, command=lambda: self._open_path(self.app_root / "03_PROCESSED")).pack(anchor="w", pady=4)

    def setup_dataset_workspace(self, parent):
        root = ctk.CTkFrame(parent, fg_color="#0f1419")
        root.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(root, text="DATASET", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            root,
            text="Export in 04_DATASET (JSONL per task, correlations.json, summary).",
            font=("Segoe UI", 12),
            text_color="#9e9e9e",
        ).pack(anchor="w", pady=(4, 12))
        row = ctk.CTkFrame(root, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkButton(row, text="Rigenera dataset (pipeline reports-only)", width=280, command=self._rebuild_dataset_from_gui).pack(side="left", padx=(0, 10))
        ctk.CTkButton(row, text="Apri 04_DATASET", width=160, command=lambda: self._open_path(self.app_root / "04_DATASET")).pack(side="left")
        self.dataset_list = ctk.CTkTextbox(root, height=320, font=("Consolas", 11))
        self.dataset_list.pack(fill="both", expand=True, pady=12)
        self._refresh_dataset_listbox()

    def setup_knowledge_workspace(self, parent):
        root = ctk.CTkFrame(parent, fg_color="#0f1419")
        root.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(root, text="KNOWLEDGE", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            root,
            text="API provider, cataloghi, Physically Based, file in 06_KNOWLEDGE_BASE/sources.",
            font=("Segoe UI", 12),
            text_color="#9e9e9e",
            wraplength=920,
            justify="left",
        ).pack(anchor="w", pady=(4, 14))
        grid = ctk.CTkFrame(root, fg_color="transparent")
        grid.pack(fill="x")
        ctk.CTkButton(grid, text="Provider Info (AmbientCG / PB)", width=220, command=self.fetch_provider_info).grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(grid, text="Catalog page (20)", width=180, command=self.fetch_provider_catalog_page).grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(grid, text="Apri sources/api", width=160, command=lambda: self._open_path(self.app_root / "06_KNOWLEDGE_BASE" / "sources" / "api")).grid(row=0, column=2, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(grid, text="Apri mappings & rules", width=180, command=lambda: self._open_path(self.app_root / "06_KNOWLEDGE_BASE" / "mappings")).grid(row=1, column=0, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(grid, text="Apri reports", width=160, command=lambda: self._open_path(self.app_root / "06_KNOWLEDGE_BASE" / "reports")).grid(row=1, column=1, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(grid, text="Apri logs sessione", width=180, command=lambda: self._open_path(self.app_root / "logs")).grid(row=1, column=2, padx=6, pady=6, sticky="ew")

    def setup_pipeline_workspace(self, parent):
        root = ctk.CTkFrame(parent, fg_color="#0f1419")
        root.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(root, text="PIPELINE", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(
            root,
            text="Esecuzione headless completa senza re-import: ingest, validazione, benchmark, maschere, correlazioni, dataset, quality gates.",
            font=("Segoe UI", 12),
            text_color="#9e9e9e",
            wraplength=920,
            justify="left",
        ).pack(anchor="w", pady=(4, 12))
        row = ctk.CTkFrame(root, fg_color="transparent")
        row.pack(fill="x", pady=6)
        ctk.CTkButton(row, text="Run pipeline (skip import)", width=240, height=38, fg_color="#2e7d32", command=self._run_pipeline_reports_thread).pack(side="left", padx=(0, 10))
        ctk.CTkButton(row, text="Apri pipeline_run_report.json", width=240, command=self._open_latest_pipeline_report).pack(side="left")
        self.pipeline_log = ctk.CTkTextbox(root, height=340, font=("Consolas", 10), wrap="word")
        self.pipeline_log.pack(fill="both", expand=True, pady=12)

    def _append_log(self, widget: ctk.CTkTextbox, text: str):
        widget.configure(state="normal")
        widget.insert("end", text + "\n")
        widget.see("end")
        widget.configure(state="disabled")

    def _open_path(self, path: Path):
        path.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:
            messagebox.showerror("Open path", str(exc))

    def _open_external_generator_config(self):
        p = self.app_root / "config" / "external_generator.json"
        if not p.exists():
            p.write_text("{}", encoding="utf-8")
        self._open_path(p.parent)

    def _reload_vault(self):
        if not self.importer:
            return
        self.project_materials = self.importer.load_existing_vault()
        self.refresh_builder_ui()
        self._append_log(self.ingest_log, "Vault ricaricato da disco.")

    def _run_ingest_only(self):
        if not self.orchestrator:
            self._append_log(self.ingest_log, "Backend non disponibile.")
            return

        def work():
            try:
                r = self.orchestrator.ingestor.run_full_ingestion()
                msg = json.dumps(r, indent=2, ensure_ascii=False)[:8000]
                self.after(0, lambda: self._ingest_done(msg))
            except Exception as exc:
                self.after(0, lambda: self._ingest_done(f"ERROR: {exc}"))

        self.ingest_log.configure(state="normal")
        self.ingest_log.delete("0.0", "end")
        self.ingest_log.configure(state="disabled")
        self._append_log(self.ingest_log, "Ingestion in corso…")
        threading.Thread(target=work, daemon=True).start()

    def _ingest_done(self, msg: str):
        self.ingest_log.configure(state="normal")
        self.ingest_log.delete("0.0", "end")
        self.ingest_log.insert("0.0", msg)
        self.ingest_log.configure(state="disabled")

    def _refresh_dataset_listbox(self):
        d = self.app_root / "04_DATASET"
        lines = []
        if d.exists():
            for p in sorted(d.iterdir()):
                if p.is_file():
                    lines.append(f"{p.name}  ({p.stat().st_size} bytes)")
        self.dataset_list.configure(state="normal")
        self.dataset_list.delete("0.0", "end")
        self.dataset_list.insert("0.0", "\n".join(lines) if lines else "(vuoto — esegui Pipeline o Forge)")
        self.dataset_list.configure(state="disabled")

    def _rebuild_dataset_from_gui(self):
        if not self.orchestrator:
            return

        def work():
            try:
                self.orchestrator.run_reports_only()
                self.after(0, lambda: (self._refresh_dataset_listbox(), messagebox.showinfo("Dataset", "Dataset e report aggiornati.")))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("Dataset", str(exc)))

        threading.Thread(target=work, daemon=True).start()

    def _run_pipeline_reports_thread(self):
        if not self.orchestrator:
            self._append_log(self.pipeline_log, "Backend non disponibile.")
            return

        def work():
            try:
                rep = self.orchestrator.run_reports_only()
                txt = json.dumps(rep, indent=2, ensure_ascii=False)[:12000]
                self.after(0, lambda: self._pipeline_done(txt))
            except Exception as exc:
                self.after(0, lambda: self._pipeline_done(f"ERROR: {exc}"))

        self.pipeline_log.configure(state="normal")
        self.pipeline_log.delete("0.0", "end")
        self.pipeline_log.configure(state="disabled")
        self._append_log(self.pipeline_log, "Pipeline in esecuzione (skip import)…")
        threading.Thread(target=work, daemon=True).start()

    def _pipeline_done(self, text: str):
        self.pipeline_log.configure(state="normal")
        self.pipeline_log.delete("0.0", "end")
        self.pipeline_log.insert("0.0", text)
        self.pipeline_log.configure(state="disabled")
        self._refresh_dataset_listbox()

    def _open_latest_pipeline_report(self):
        p = self.app_root / "06_KNOWLEDGE_BASE" / "reports" / "pipeline_run_report.json"
        if p.exists():
            self._open_path(p.parent)
        else:
            messagebox.showwarning("Report", "File non trovato. Esegui prima la pipeline.")

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
        segmented = int(res.get("stages", {}).get("pid_mask_engine", {}).get("masks_generated", 0))
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
            if hasattr(self, "_refresh_dataset_listbox"):
                self._refresh_dataset_listbox()
        else:
            errors = res.get("stages", {}).get("ingestion", {}).get("errors", 0)
            messagebox.showerror("Forge Error", f"{summary_msg}\nErrors: {errors}")


if __name__ == "__main__":
    app = SignumSentinelGUI()
    app.mainloop()
