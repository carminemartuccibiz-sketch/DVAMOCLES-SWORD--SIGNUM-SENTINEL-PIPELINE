# DVAMOCLES SWORD - SIGNUM SENTINEL

Pipeline Python per ingestione PBR, validazione fisica, arricchimento AI e costruzione dataset training.

Obiettivo: trasformare asset texture eterogenei in una base dati coerente, tracciabile e training-ready, mantenendo distinzione rigorosa tra file RAW e CUSTOM.

## Scopo del progetto

- ingestione di materiali PBR da cartelle drag-and-drop o import guidato GUI
- classificazione mappe e varianti (`albedo`, `normal`, `roughness`, etc.) con naming intelligence
- estrazione metadati tecnici (risoluzione, bit depth, color space) via ExifTool/OpenCV
- validazione fisica con regole centralizzate nella Knowledge Base
- generazione manifest JSON completi per catalogazione e dataset AI
- tracciamento provenance (`source_raw`, `process`) per ogni asset CUSTOM

## Architettura directory

- `01_RAW_ARCHIVE/`: archivio originale, fonte primaria non alterata
- `02_CUSTOM/`: derivati e trasformazioni custom
- `03_PROCESSED/`: output intermedi di pipeline
- `04_DATASET/`: dataset finali per training
- `05_OUTPUT/`: export finali
- `06_KNOWLEDGE_BASE/`: regole, mapping, manifest, fonti di conoscenza
- `core/`: moduli principali del sistema
- `ai/`: moduli AI addizionali
- `utils/`: helper tecnici
- `config/`, `logs/`, `temp/`: configurazione, log, runtime
- `Z_DEV/`: contesto e documentazione storica/operativa

## Moduli core principali

- `main_gui.py`: entrypoint GUI (CustomTkinter + TkinterDnD)
- `core/import_assistant.py`: orchestrazione import, auto-detect, scrittura manifest/process
- `core/naming_intelligence.py`: naming map-type guidato da KB JSON
- `core/metadata_extractor.py`: metadata extraction (ExifTool portabile + fallback OpenCV)
- `core/pbr_validator.py`: validator unificato con regole PBR da JSON
- `core/knowledge_ingestor.py`: ingestione conoscenza esterna in `06_KNOWLEDGE_BASE`

## Single Source of Truth

Le regole non devono essere hardcoded nei moduli Python:

- naming patterns: `06_KNOWLEDGE_BASE/mappings/naming_map.json`
- regole fisiche: `06_KNOWLEDGE_BASE/rules/pbr_rules.json`
- indicizzazione conoscenza: `06_KNOWLEDGE_BASE/kb_index.json`
- manifest materiali: `06_KNOWLEDGE_BASE/Manifests/*_manifest.json`

## Flusso operativo

1. import cartelle/file da GUI in staging
2. auto-detect file (metadata + visual check + naming intelligence + caption AI opzionale)
3. auto-sort nel vault materiali/varianti
4. editing metadati in inspector (material/folder/file)
5. `EXECUTE FORGE` per import definitivo in RAW/CUSTOM
6. scrittura `material_info.json`, `process.json` e manifest KB

## RAW vs CUSTOM (contratto dati)

- RAW: file originali vendor/user non trasformati
- CUSTOM: file generati/modificati da pipeline o tool esterni
- per ogni file CUSTOM sono obbligatori:
  - `source_raw`
  - `process`

Questo e' fondamentale per training supervisionato e audit della provenance.

## Ingestione knowledge base esterna

Per importare fonti testuali/CSV nel catalogo KB:

```python
from core.knowledge_ingestor import KnowledgeIngestor

files = [
    r"c:/Users/Carmine/Desktop/DATI GREZZI PER TRAINING/PBR_Master_Knowledge_Base_Part1.md",
    r"c:/Users/Carmine/Desktop/DATI GREZZI PER TRAINING/PBR_MKB_ParteA.md",
    r"c:/Users/Carmine/Desktop/DATI GREZZI PER TRAINING/PBR_MKB_ParteB.md",
    r"c:/Users/Carmine/Desktop/DATI GREZZI PER TRAINING/SpectralDB - spectraldb.csv",
    r"c:/Users/Carmine/Desktop/DATI GREZZI PER TRAINING/Thunderbit_4566a5_20260411_173917.csv",
]

print(KnowledgeIngestor().ingest_files(files))
```

Output:

- copia sorgenti in `06_KNOWLEDGE_BASE/sources/<ext>/`
- indice documenti in `06_KNOWLEDGE_BASE/kb_index.json`
- tokenizzazione base per supporto catalogazione e query

## Toolchain e dipendenze

- Python 3.12 (consigliato)
- GUI: `customtkinter`, `tkinterdnd2`
- imaging: `Pillow`, `opencv-python`
- AI vision: `torch`, `transformers` (BLIP)
- sistema: `psutil`, `gputil`
- metadata: ExifTool (portabile supportato)

Script utili:

- `install_dependencies.bat`: install/update dipendenze (venv-aware, fallback torch CPU)
- `START_FORGE.bat`: launcher GUI

## Note operative

- se l'AI non e' attiva, il sistema resta operativo in modalita' metadata+naming+opencv
- se ExifTool non e' disponibile, viene usato fallback OpenCV/Pillow
- i file di contesto e guida sono conservati in `Z_DEV/contesto e co ai/`
