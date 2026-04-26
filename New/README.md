# DVAMOCLES SWORD — SIGNUM SENTINEL (New root)

PBR material intelligence pipeline: ingest, validate, enrich (BLIP + optional Ollama), segment, correlate, export training datasets. This tree follows **SIGNUM_SENTINEL_PIPELINE_SPEC_CURSOR.md** (see `docs/SPEC_REFERENCE.md`).

## Layout

| Path | Role |
|------|------|
| `01_RAW_ARCHIVE/` | Read-only vendor originals |
| `02_CUSTOM/` | Derived assets + mandatory `process.json` |
| `03_PROCESSED/` | Manifests and analysis intermediates |
| `04_DATASET/` | JSONL tasks + `correlations.json` + summaries |
| `04_SEGMENTATION/` | Mask outputs (intermediate) |
| `05_OUTPUT/` | Engine exports (UE/Unity/Godot) |
| `06_KNOWLEDGE_BASE/` | `naming_map.json`, `pbr_rules.json`, sources, manifests |
| `core/` | Deterministic pipeline |
| `ai/` | HuggingFace BLIP, Ollama client, tagging, crawler |
| `oracle/` | Physics Oracle (KB-backed, read-only rules) |
| `utils/` | Paths, logging, ExifTool resolver, image helpers |

## GUI (Blender-style workspaces)

La finestra principale usa **workspace** a schermo intero: **Import**, **Vault**, **Inspect**, **Ingest**, **Generate**, **Dataset**, **Knowledge**, **Pipeline**. Barra in alto (segmented) + **Ctrl+Tab** per ciclare. L’ultimo workspace è salvato in `config/gui_state.json`.

## Run

1. `cd` into this folder (`New`).
2. `install_dependencies.bat` (creates/uses `venv` if present).
3. `START_FORGE.bat` — GUI. Optional: `python main_pipeline.py --reports-only` for headless stages after import.

Place portable ExifTool at `exiftool_files/exiftool.exe` (optional; OpenCV/Pillow fallback exists).

## Python

Target **3.12**. Stack includes `torch`, `transformers`, `diffusers`, `accelerate`, `huggingface_hub`, `opencv-python`, `customtkinter`, `tkinterdnd2`.

## Single source of truth

Do not hardcode map rules in Python: edit `06_KNOWLEDGE_BASE/mappings/naming_map.json` and `06_KNOWLEDGE_BASE/rules/pbr_rules.json` first.
