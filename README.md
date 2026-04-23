# 🗡️ DVAMOCLES SWORD™ – SIGNUM SENTINEL
**Material Forge Studio® - Master Pipeline & AI Training Forge**

Questa è una pipeline Python production-ready progettata per l'acquisizione, l'analisi profonda, la generazione procedurale e la costruzione di dataset per materiali PBR (Physically Based Rendering). 
Non è un semplice convertitore di texture: è una fornace automatizzata per addestrare modelli AI comprendendo il "DNA fisico" e i processi di creazione dei materiali.

---

## 📁 ARCHITETTURA DIRECTORY (STRICT RIGOR)
Il sistema è diviso in aree di competenza isolate. Le regole di Lettura/Scrittura sono ferree.

* `01_RAW_ARCHIVE/`  → Dati originali "Puri" scaricati dai provider (es. Quixel, AmbientCG). **(Solo Lettura, MAI modificare)**
* `02_CUSTOM/`       → Dati generati o modificati dall'utente (es. scan, output di Substance, file `.uasset` di Unreal Engine). Include i manifest `process.json`. **(Input/Lettura)**
* `03_PROCESSED/`    → Output intermedio standardizzato. File raggruppati per risoluzione, analizzati e con manifest JSON associati. **(Scrittura Pipeline)**
* `04_DATASET/`      → Output formattato per il training AI (JSON enormi, mapping, split train/test). **(Scrittura Pipeline)**
* `05_OUTPUT/`       → Export finali ottimizzati per specifici Engine (Unreal, Unity). **(Scrittura Pipeline)**
* `06_KNOWLEDGE_BASE/`→ "L'Oracolo". Contiene PDF, Markdown e CSV processati che dettano le regole PBR (es. "L'Albedo del carbone è 30-40").
* `core/`            → Cuore logico in Python (Importer, Ingestor, Naming, Metadata).
* `utils/`           → Script helper (Seamless ops, OpenCV wrappers).
* `ai/`              → Moduli di intelligenza artificiale (Vision, SAM, Image2Text).
* `oracle/`          → Moduli per la validazione contro le regole PBR.
* `logs/`            → File di log di sistema e storici.

---

## 🔁 THE AI FORGE PIPELINE (LE 6 FASI)

### 🟩 FASE 1: ACQUISITION & CONTEXT (The Gatekeeper)
* **Modulo:** `core/import_assistant.py` (L'Importer)
* **Azione:** Riceve interi set di texture (incluse multi-risoluzioni 1K, 2K, 4K). Smista tra RAW e CUSTOM in base all'input umano. Salva il contesto di creazione (tag, provider, logica di derivazione).

### 🟦 FASE 2: TECHNICAL EXTRACTION (The Brain)
* **Moduli:** `core/ingestor.py`, `core/naming_intelligence.py`, `core/metadata_extractor.py`
* **Azione:** Raggruppa i file per materiale e risoluzione. Usa regex per capire il tipo di mappa ed estrae il DNA tecnico con ExifTool/OpenCV (Bit Depth, Spazio Colore, Profilo ICC). Crea il `manifest.json`.

### 🟧 FASE 3: PHYSICAL VALIDATION & GENERATION (The Forger)
* **Moduli:** `core/validator.py`, `core/map_generator.py`
* **Azione:** Verifica le mancanze. Se manca una mappa (es. Height) e l'utente lo richiede, usa algoritmi/AI (es. DeepBump, img2texture) per generarla a partire da altre mappe. 
* **Focus AI:** Registra meticolosamente cosa è "Reale" e cosa è "Generato" per insegnare all'AI a cogliere le differenze.

### 🟨 FASE 4: VISUAL ENRICHMENT (L'Occhio dell'AI)
* **Moduli:** `ai/vision_describer.py`, `ai/mask_generator.py`
* **Azione:** Modelli Vision-to-Text descrivono semanticamente il materiale. Meta SAM (Segment Anything) crea PID Masks (maschere di segmentazione) per distinguere materiali diversi nella stessa texture (es. mattone vs muschio).

### 🟪 FASE 5: THE ORACLE (Knowledge Integration)
* **Moduli:** `core/knowledge_processor.py`, `oracle/pbr_judge.py`
* **Azione:** Mastica documenti complessi dalla `06_KNOWLEDGE_BASE` e li trasforma in "Ground Truth" matematiche contro cui il Validator può testare le texture.

### ⬛ FASE 6: THE DATASET BUILDER
* **Modulo:** `core/dataset_builder.py`
* **Azione:** Collassa le Fasi 1-5 in un super-dataset dentro `04_DATASET`, pronto per l'addestramento o il fine-tuning di modelli AI custom.

---

## ⚙️ REGOLE DI SVILUPPO
1. **Fallback Sicuri:** Se un tool AI o una libreria (es. ExifTool, OpenCV, Ollama) fallisce, il sistema non deve crashare. Deve loggare l'errore e usare parametri di default (es. `resolution: unknown`).
2. **Niente Codice Stub:** Tutto il codice Python deve essere produzione-pronto e strutturato ad oggetti.
3. **Tracciabilità:** Qualsiasi azione trasformativa su un'immagine (es. resize, normalizzazione colore) deve essere scritta nel `manifest.json`.
