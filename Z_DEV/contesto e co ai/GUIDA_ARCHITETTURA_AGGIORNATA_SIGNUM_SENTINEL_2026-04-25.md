# DVAMOCLES SWORD - Guida Architettura Aggiornata (2026-04-25)

Questa guida aggiorna i documenti storici presenti in `Z_DEV/contesto e co ai/` e definisce lo stato tecnico corrente del sistema SIGNUM SENTINEL.

## 1) Principi Architetturali Correnti

- Single Source of Truth: regole e pattern vivono nei JSON di `06_KNOWLEDGE_BASE`.
- Entry point operativo GUI: `main_gui.py` (CustomTkinter + TkinterDnD).
- Distinzione hard tra RAW e CUSTOM per training dataset.
- Provenance obbligatoria per ogni file CUSTOM.

## 2) Struttura Moduli (stato reale)

- `core/import_assistant.py`: orchestrazione ingest, auto-detect, import, manifest.
- `core/naming_intelligence.py`: classificazione naming guidata da `naming_map.json`.
- `core/metadata_extractor.py`: metadati tecnici con ExifTool portabile + fallback OpenCV.
- `core/pbr_validator.py`: validator unificato (rule-based + map generation).
- `core/visual_analyzer.py` / `core/vision_engine.py`: analisi pixel e visione AI.

## 3) Knowledge Base (sorgenti)

- Naming: `06_KNOWLEDGE_BASE/mappings/naming_map.json`
  - `map_patterns`
  - `role_aliases`
  - `normal_convention_patterns` (DX/GL)
- Regole fisiche: `06_KNOWLEDGE_BASE/rules/pbr_rules.json`
- Manifest materiali: `06_KNOWLEDGE_BASE/Manifests/*_manifest.json`

## 4) RAW vs CUSTOM (contratto dati)

Per ogni file CUSTOM devono essere presenti:

- `source_raw`: riferimento al file sorgente RAW
- `process`: descrizione della trasformazione (es. `custom_transform`, `normal_from_height`, ecc.)

Nel flusso di import:

- RAW -> scrittura in `01_RAW_ARCHIVE/<Provider>/<Materiale>/...`
- CUSTOM -> scrittura in `02_CUSTOM/<Provider>/<Materiale>/...`
- Generazione/aggiornamento manifest in `06_KNOWLEDGE_BASE/Manifests`

## 5) ExifTool Portabile (policy)

Risoluzione percorso ExifTool:

1. `./exiftool.exe`
2. `./exiftool_files/exiftool.exe`
3. `./exiftool_files/exiftool(-k).exe`
4. fallback `PATH` (`shutil.which("exiftool")`)
5. fallback finale OpenCV/Pillow per lettura dimensioni di base

## 6) Cleanup e Dedup già effettuati

- Rimossa logica Oracle duplicata (`oracle/` deprecata)
- Validator unico: `core/pbr_validator.py`
- Regole unificate in `pbr_rules.json`
- Naming normal convention spostato da regex hardcoded a KB JSON

## 7) Linee guida operative per i prossimi sprint

- Evitare hardcoding di regole mappe nei moduli Python.
- Qualsiasi nuova convenzione naming va aggiunta prima in `naming_map.json`.
- Ogni modifica a process/provenance va verificata sui manifest reali.
- Preparare i path con resolver bundle-safe (step successivo: compatibilita' PyInstaller).

## 8) Stato Roadmap

- PHASE 1: completata
- PHASE 2: completata
- PHASE 3: in avanzamento (provenance CUSTOM + ExifTool portabile completati lato core)
- PHASE 4/5: da eseguire (lazy loading esteso e packaging single executable)
