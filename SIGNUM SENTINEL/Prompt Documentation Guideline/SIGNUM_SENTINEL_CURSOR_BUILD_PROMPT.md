# DVAMOCLES SWORD™ — SIGNUM SENTINEL v3.0
## Cursor AI Build Prompt — Complete System Specification
**Version: 3.0-CURSOR | Date: 2026-04-27 | Authority: DVAMOCLES_3.1-FINAL + SENTINEL_SPEC_v3 + Codebase Git**
**Status: DEVELOPMENT-READY — Feed this file + codebase root to Cursor as primary context**

---

## 0. COME USARE QUESTO DOCUMENTO IN CURSOR

Questo file è il **prompt master** per costruire SIGNUM SENTINEL da zero o continuare
lo sviluppo del codebase esistente. Usarlo così:

1. Apri Cursor nella root del repository (`DVAMOCLES SWORD- SIGNUM SENTINEL PIPELINE/`)
2. Aggiungi questo file come **Context** permanente in ogni chat Cursor
3. Aggiungi anche `DVAMOCLES_3.1-FINAL_EN_AI-Ready.md` come second context
4. Usa il `.cursorrules` presente nella sezione 16 di questo documento
5. Mantieni **entrambe** le root (`/` e `/New/`) — sono versioni parallele in evoluzione

**Regola di priorità fonte:**
```
DVAMOCLES_3.1-FINAL_EN_AI-Ready.md  →  architettura e comportamento
UPDATED_MVP_SPEC.md                  →  implementation details Phase 1
Minimum_Functional_Core              →  MFC end-to-end test
Questo file                          →  SIGNUM SENTINEL pipeline + integrazioni esterne
```

---

## 1. COS'È DAVVERO QUESTO SISTEMA

SIGNUM SENTINEL non è un importer di texture. È un **sistema di industrializzazione del dato PBR**:

```
INPUT:  texture sporche, random, non strutturate (da internet, fotogrammetria, SD, etc.)
        ↓
PROCESS: validazione fisica → strutturazione → correlazione → arricchimento AI
        ↓
OUTPUT-A: dataset AI-ready (training set per modelli di material intelligence)
OUTPUT-B: asset engine-ready (UE5, Unity, Godot — The Definitive 5 format)
```

È simultaneamente tre cose:
- **Dataset Factory** per addestrare l'AI di DVAMOCLES SWORD™
- **Material Physics Engine** che valida fisicamente ogni materiale
- **Foundation Layer** del sistema AI che diventerà embedded nel software finale

---

## 2. ARCHITETTURA GLOBALE

### 2.1 Pattern Obbligatori — Non Negoziabili

```
Event Bus (pub/sub asyncio)        →  NESSUN modulo modifica stato globale direttamente
Command Pattern                    →  ogni mutazione è un Command atomico reversibile
Worker Thread per tutto il pesante →  UI non si blocca mai
AI Hook isolation                  →  AI riceve snapshot, non muta mai stato direttamente
Proxy System                       →  Working Resolution ≠ Export Resolution
Knowledge Base as SSOT             →  ZERO logica hardcoded nei moduli Python
```

### 2.2 Layer Mapping — SIGNUM SENTINEL dentro DVAMOCLES

```
SIGNUM SENTINEL Module      │  DVAMOCLES Layer      │  Responsabilità
────────────────────────────┼───────────────────────┼──────────────────────────────
Import Assistant            │  Layer 0              │  Staging, detection, gating
Ingestor                    │  Layer 0–1            │  Strutturazione set materiale
Naming Intelligence (NID)   │  Layer 0              │  filename → map_type (da KB)
Metadata Extractor          │  Layer 0              │  ExifTool + Pillow fallback
Universal Parser            │  Layer 0              │  .mtlx / .tres → mapping
Generator                   │  Layer 1              │  Conversioni deterministiche
Correlation Engine          │  Layer 1–2            │  SSIM, PSNR, FFT, LAB
PBR Validator               │  Layer 2              │  Physics Oracle check
P-ID Mask Engine            │  Layer 2              │  Segmentazione zone fisiche
AI Vision Engine            │  AI Hooks             │  BLIP / LLaVA (on-demand)
Ollama Client               │  AI System            │  LLM locale (solo JSON)
Knowledge Processor         │  Layer 0 (SSOT)       │  KB management + HF datasets
Dataset Builder             │  Layer 4 export       │  master.json / raw.json / SQLite
Pipeline Orchestrator       │  Coordina tutto       │  Sequenza + Event Bus
```

### 2.3 Topologia Event Bus

```python
# Topic Map — tutti gli eventi del sistema
EVENTS = {
    # Import
    "import.staging.started":     "asset_path, staging_id",
    "import.detection.completed": "staging_id, detection_result",
    "import.user.confirmed":      "staging_id, user_overrides",
    "import.completed":           "material_id, raw_path",

    # Ingestion
    "ingest.started":             "material_id",
    "ingest.variant.detected":    "material_id, variant_name, file_list",
    "ingest.completed":           "material_id, manifest_path",

    # Processing
    "metadata.extracted":         "file_id, metadata_dict",
    "naming.classified":          "file_id, map_type, confidence",
    "generator.map.created":      "file_id, output_path, process_json",
    "validation.failed":          "material_id, violations_list",
    "validation.passed":          "material_id",

    # AI
    "ai.caption.requested":       "file_id, image_path",
    "ai.caption.completed":       "file_id, caption, tags",
    "ai.vision.unloaded":         "model_id",

    # Knowledge
    "knowledge.updated":          "source, added_count",

    # Dataset
    "dataset.ready":              "output_paths_dict",
    "pipeline.completed":         "summary_stats",
}
```

---

## 3. FILESYSTEM — LAYOUT OBBLIGATORIO

```
DVAMOCLES_PROJECT/
│
├── 01_RAW_ARCHIVE/          ← READ ONLY. MAI modificare. MAI.
│   └── {Provider}/
│       └── {MaterialName}/
│           ├── material_info.json
│           └── variants/
│               └── {1K_PNG}/
│                   └── *.png / *.tga / *.exr
│
├── 02_CUSTOM/               ← File generati/derivati. OGNI file ha process.json.
│   └── {Provider}/
│       └── {MaterialName}/
│           ├── process.json
│           └── variants/
│               └── {1K_PNG_GEN}/
│                   └── *.png
│
├── 03_PROCESSED/            ← Set strutturati con manifest e correlazioni
│   └── {Provider}/
│       └── {MaterialName}/
│           ├── manifest.json
│           ├── correlations.json
│           ├── physics_validation.json
│           └── variants/
│               └── {1K_PNG}/
│                   └── *.png (copie processate)
│
├── 04_DATASET/              ← Output finale AI-ready
│   ├── master.json          (runtime-light, veloce)
│   ├── raw.json             (training-complete, pesante)
│   ├── database.db          (SQLite index opzionale)
│   └── correlations.json    (append-only)
│
├── 05_OUTPUT/               ← Export engine-ready (UE5, Unity, Godot)
│   └── {MaterialName}/
│       ├── UE5/
│       ├── Unity_HDRP/
│       └── Godot/
│
├── 06_KNOWLEDGE_BASE/       ← SINGLE SOURCE OF TRUTH. Logica nei JSON, non nel codice.
│   ├── mappings/
│   │   ├── naming_map.json          ← NID patterns + role aliases (UNICO posto)
│   │   ├── texture_rules.json       ← Regole validazione per tipo mappa
│   │   └── polycount_rules.json     ← Riferimenti Polycount
│   ├── rules/
│   │   └── pbr_rules.json           ← Profili fisici materiali + validation rules
│   ├── sources/
│   │   ├── md/                      ← Documentazione grezza ingesta
│   │   ├── api/                     ← Cache API (AmbientCG, PhysicallyBased)
│   │   └── csv/                     ← Dataset CSV (IOR, SpectralDB)
│   ├── parsed/
│   │   └── source_summaries.json
│   ├── Manifests/
│   │   └── {MaterialName}_manifest.json
│   ├── patterns/
│   │   └── import_learning.json     ← NID learner output
│   └── schemas/
│       ├── material_info.schema.json
│       └── process.schema.json
│
├── logs/
│   ├── last_session.log             ← Sovrascritta ogni sessione
│   └── session_1.log … session_5.log  ← Rotazione max 5
│
├── temp/
│   └── staging/                     ← Staging area temporanea (UUID per sessione)
│       └── {uuid}/
│
├── core/                            ← Moduli pipeline Python
├── ai/                              ← AI stack (BLIP, Ollama, crawler)
├── oracle/                          ← Physics Oracle (JSON + helpers)
├── utils/                           ← Helpers (paths, logger, exiftool)
├── New/                             ← Root parallela (versione più recente)
├── main_gui.py
├── main_pipeline.py
├── requirements.txt
└── .cursorrules
```

### Hard Rules Filesystem
```
❌  01_RAW_ARCHIVE/ non si tocca mai — nemmeno per rinominare
✅  ogni file in 02_CUSTOM/ deve avere un process.json con parent + operations + hash
❌  logica di naming/validazione hardcoded nei .py
✅  tutta la logica nei JSON in 06_KNOWLEDGE_BASE/
❌  RAW e CUSTOM nella stessa cartella
✅  struttura Provider/Material/variants/{resolution}_{format}/
```

---

## 4. JSON SCHEMAS CANONICI

### 4.1 material_info.json
```json
{
  "schema_version": "1.0.0",
  "identity": {
    "material_name": "Tiles_138",
    "provider": "AmbientCG",
    "asset_type": "RAW",
    "source": "API_IMPORT",
    "source_url": "https://ambientcg.com/a/Tiles138",
    "technique": "Photogrammetry",
    "category": "stone",
    "import_date": "2026-04-27T10:00:00Z"
  },
  "description": "Worn stone tiles with visible grout",
  "tags": ["tiles", "stone", "seamless", "worn"],
  "resolution_list": ["1K", "2K", "4K"],
  "variants": {
    "2K_PNG": {
      "files": [
        {
          "name": "Tiles138_2K_Color.jpg",
          "map_type": "ALBEDO",
          "confidence": 0.95,
          "color_space": "sRGB",
          "bit_depth": "8-bit",
          "tech_res": "2048x2048",
          "resolution": "2K",
          "format": "JPG",
          "source_raw": "Tiles138_2K_Color.jpg"
        }
      ]
    }
  }
}
```

### 4.2 process.json (per ogni file in 02_CUSTOM/)
```json
{
  "schema_version": "1.0.0",
  "timestamp": "2026-04-27T10:05:00Z",
  "material_name": "Tiles_138",
  "provider": "AmbientCG",
  "asset_type": "CUSTOM",
  "pipeline": [
    {
      "output": "Tiles138_2K_Normal_GEN.png",
      "derived_from": ["Tiles138_2K_Height.png"],
      "process": "height_to_normal_sobel",
      "tool": "generator_module_v1.0",
      "parameters": {
        "strength": 1.0,
        "blur_before": 0.0,
        "convention": "DX"
      },
      "input_hash_sha256": "abc123...",
      "output_hash_sha256": "def456...",
      "confidence": 1.0
    }
  ],
  "relationships": []
}
```

### 4.3 manifest.json (in 03_PROCESSED/)
```json
{
  "schema_version": "1.0.0",
  "metadata": {
    "material_name": "Tiles_138",
    "provider": "AmbientCG",
    "source_origin": "RAW",
    "tags": ["tiles", "stone"],
    "technique": "Photogrammetry"
  },
  "coverage": {
    "maps_found": ["albedo", "normal", "roughness", "ao", "height"],
    "is_pbr_complete": true
  },
  "variants": {
    "2K_PNG": {
      "format": "PNG",
      "resolution": "2K",
      "files": [...]
    }
  },
  "stats": {
    "variant_count": 3,
    "file_count": 15
  }
}
```

### 4.4 correlations.json (append-only in 04_DATASET/)
```json
[
  {
    "timestamp_utc": "2026-04-27T10:10:00Z",
    "kind": "intra_set",
    "material": "Tiles_138",
    "variant": "2K_PNG",
    "metrics": {
      "albedo_roughness_correlation": 0.72,
      "normal_height_gradient_match": 0.89,
      "seamless_score": 0.91,
      "seam_locations": ["right_edge"],
      "lab_variance": 12.4
    }
  }
]
```

### 4.5 physics_validation.json (per materiale in 03_PROCESSED/)
```json
{
  "material": "Tiles_138",
  "profile_used": "stone_ceramic",
  "physics_compliance_score": 0.87,
  "timestamp": "2026-04-27T10:08:00Z",
  "checks": [
    {
      "check_id": "albedo_range",
      "map": "Tiles138_2K_Color.jpg",
      "status": "pass",
      "detected_mean_srgb": 148,
      "expected_range": [120, 200],
      "severity": "info"
    },
    {
      "check_id": "roughness_physical_range",
      "map": "Tiles138_2K_Roughness.jpg",
      "status": "warning",
      "detected_mean": 0.61,
      "expected_range": [0.70, 0.95],
      "severity": "warning",
      "auto_fix_applied": false
    }
  ],
  "violations": ["roughness_below_expected_for_stone"]
}
```

---

## 5. MODULO 1 — IMPORT ASSISTANT (GATEKEEPER)

**Responsabilità**: Gate unico di ingresso. Nessun file entra nel sistema senza passare da qui.

### 5.1 Entry Points Utente

```
DRAG & DROP
  ├── cartella          → analisi struttura ricorsiva (max_depth=4)
  ├── archivio .zip     → estrai in temp/staging/{uuid}/ → poi pipeline
  └── file singoli      → cerca set compatibile per prefix matching

TOOLBAR BUTTON "Import"
  └── Windows file dialog → stessa pipeline

BATCH API (headless)
  └── python main_pipeline.py --import-dir "D:/textures/"
```

### 5.2 Pipeline Interna — Detection Stack

```python
# STEP 1: Staging
staging_id = uuid4()
staging_path = temp/staging/{staging_id}/
# copia/estrai qui — NON tocca ancora RAW

# STEP 2: Detection Stack (ordine preciso)
for file in staging_files:
    # 2a. Metadata fisici
    meta = MetadataExtractor.extract(file)
    # → {resolution, bit_depth, format, color_space, software_origin}

    # 2b. Visual classification (OpenCV)
    visual = VisualAnalyzer.classify(file)
    # → {type: "NORMAL"|"ALBEDO"|"GRAYSCALE", confidence: 0.0-1.0}

    # 2c. Naming Intelligence (prima passata — da KB)
    naming = NamingIntelligence.classify_filename(file.name)
    # → {map_type, confidence, convention: "DX"|"GL"|None}

    # 2d. MaterialX / .tres sidecar check
    if .mtlx/.tres present:
        UniversalParser.parse(sidecar_file)
        # → aggiorna naming_map.json in KB (apprendimento)

    # 2e. AI Caption (solo se RGB + AI loaded)
    if visual.type == "COLOR" and ai_model_loaded:
        caption = AIVisionEngine.caption(file)
        # → "weathered stone tiles with visible grout"

# STEP 3: Smart Grouping
groups = smart_group_by_prefix_and_nid(files)
# → ProposedMaterialGroups[]

# STEP 4: Analyzer UI — Human-in-the-Loop
analyzer_ui.show(groups)
# → User vede: grouping suggerito, mappe rilevate, confidence, errori
# → User può: correggere map_type, rinominare, dividere/unire gruppi, approva/rigetta

# STEP 5: Post-conferma
if user.confirmed:
    copy_to_raw_archive(confirmed_files)
    write_material_info_json()
    EventBus.publish("import.completed", material_id)
    # → trigger automatico Ingestor
```

### 5.3 Output

```
01_RAW_ARCHIVE/{Provider}/{MaterialName}/
├── material_info.json           ← schema §4.1
└── variants/{1K_PNG}/
    └── *.texture_files
```

---

## 6. MODULO 2 — INGESTOR

**Responsabilità**: Trasforma struttura raw disorganizzata in set strutturati con manifest.

### 6.1 Logica Grouping

```python
# Variant detection da folder name
"Rock_055_2K_PNG"  →  material="Rock_055", variant="2K_PNG"
"Rock_055_4K_JPEG" →  material="Rock_055", variant="4K_JPEG"

# Packed map expansion
"Rock_ORM.png" →  MaterialGroup.assets["ORM_Packed"] = asset
                  # expand logico: R=AO, G=Roughness, B=Metallic (virtual channels)

# Ghost Asset per mappe mancanti
if "Normal" not in found_maps:
    ghost = GhostAsset(channel="Normal", constant=0.5)
    # workflow continua senza bloccarsi
```

### 6.2 Output

```
03_PROCESSED/{Provider}/{MaterialName}/
├── manifest.json               ← schema §4.3
└── variants/{2K_PNG}/
    └── *.processed_files
```

---

## 7. MODULO 3 — NAMING INTELLIGENCE (NID)

**Responsabilità**: Classificare ogni filename in un `map_type` canonico. SSOT = KB JSON.

### 7.1 Architettura a Priorità

```
PRIORITY 1: User Overrides          → 06_KNOWLEDGE_BASE/mappings/naming_map.json
PRIORITY 2: Vendor Packs (.DVNC)    → vendor-specific override files
PRIORITY 3: Built-in Rules          → 06_KNOWLEDGE_BASE/mappings/naming_map.json
```

**CRITICO**: Tutti i pattern sono in `naming_map.json`. ZERO pattern hardcoded in Python.

### 7.2 naming_map.json Structure
```json
{
  "map_patterns": {
    "albedo":    ["_BC", "_Albedo", "_BaseColor", "_Color", "_Diffuse", "_Col"],
    "normal":    ["_N", "_Normal", "_NRM", "_Norm", "_NormalMap"],
    "roughness": ["_R", "_Roughness", "_Rough", "_RGH"],
    "metallic":  ["_M", "_Metallic", "_Metal", "_MTL"],
    "ao":        ["_AO", "_Occlusion", "_Occ", "_AmbientOcclusion"],
    "height":    ["_H", "_Height", "_Disp", "_Displacement"],
    "orm_packed": ["_ORM", "_ARM"],
    "rma_packed": ["_RMA"]
  },
  "role_aliases": {
    "basecolor": "albedo",
    "diffuse": "albedo",
    "color": "albedo",
    "normalmap": "normal",
    "roughnessmap": "roughness",
    "ambientocclusion": "ao",
    "displacement": "height"
  },
  "normal_convention_patterns": {
    "dx": ["_NormalDX", "_NRM_DX", "_normal_dx"],
    "gl": ["_NormalGL", "_NRM_GL", "_normal_gl"]
  }
}
```

### 7.3 Confidence Scoring
```python
def calculate_confidence(filename, pattern_list, detected_channels):
    score = 0.0
    name_lower = Path(filename).stem.lower()
    tokens = re.split(r"[_\-. ]+", name_lower)

    for suffix in pattern_list:
        s = suffix.lower().lstrip("_")
        if s in tokens:
            score = 0.99   # exact token match
            break
        if s in name_lower:
            score = max(score, 0.75)  # substring match

    # Channel structure confirmation
    if detected_channels in expected_channels_for_type:
        score = min(1.0, score + 0.05)

    return score

# Threshold: confidence < 0.50 → "unknown" → richiede override manuale
```

---

## 8. MODULO 4 — METADATA EXTRACTOR

**Responsabilità**: Estrarre metadati tecnici fisici da ogni file texture.

### 8.1 Tool Stack
```python
# Priorità di estrazione:
# 1. ExifTool (portabile: exiftool_files/exiftool.exe o PATH)
# 2. Pillow PIL (fallback)
# 3. OpenCV (fallback per dimensioni)

def extract_all(file_path):
    raw = _get_exiftool_json(file_path)  # subprocess + -j flag
    return {
        "resolution": (W, H),
        "bit_depth": "8-bit" | "16-bit" | "32-bit float",
        "format": "PNG" | "TGA" | "EXR" | ...,
        "color_space": "sRGB" | "Linear" | "Unknown",
        "channels": 1 | 3 | 4,
        "software_origin": "Substance Designer" | "Adobe Photoshop" | "Blender" | ...,
        "metadata_raw": {raw_exif_dict}
    }
```

### 8.2 Software Origin Detection (da EXIF)
```python
ORIGIN_SIGNATURES = {
    "Substance Designer": ["substance designer"],
    "Substance Painter":  ["substance painter"],
    "Adobe Photoshop":    ["adobe photoshop"],
    "Blender":            ["blender", "blender cycles"],
    "ZBrush":             ["zbrush"],
    "Materialize":        ["materialize"],
    "Photogrammetry":     ["agisoft", "reality capture", "metashape"]
}
# Cerca in: EXIF:Software, PNG:Software, XMP:CreatorTool
```

---

## 9. MODULO 5 — UNIVERSAL PARSER (.mtlx / .tres)

**Responsabilità**: Leggere formati di descrizione materiale standard e aggiorare la KB.

### 9.1 MaterialX (.mtlx)
```python
import MaterialX as mx  # pip install MaterialX

def parse_mtlx(path):
    doc = mx.createDocument()
    mx.readFromXmlFile(doc, str(path))
    mappings = {}

    for node in doc.getNodes():
        for input_ in node.getInputs():
            if input_.getType() == "filename":
                file_value = input_.getValue()
                role = node.getName()  # e.g., "base_color", "roughness"
                mappings[Path(file_value).name] = role

    # Update KB naming_map.json con i pattern appresi
    _update_kb_from_mappings(mappings)
    return mappings

# MaterialX ha priorità massima su Naming Intelligence
# Se .mtlx presente → usa mapping da .mtlx, NID come fallback
```

### 9.2 Godot .tres
```python
def parse_tres(path):
    content = path.read_text(encoding="utf-8", errors="ignore")
    ext_resources = {}  # id → filename
    mappings = {}

    # Match [ext_resource path="..." id="..."]
    for m in re.finditer(r'\[ext_resource[^\]]*path="([^"]+)"[^\]]*id="([^"]+)"', content):
        ext_resources[m.group(2)] = Path(m.group(1)).name

    # Match slot = ExtResource("id")
    for m in re.finditer(r'([a-zA-Z0-9_]+)\s*=\s*ExtResource\("([^"]+)"\)', content):
        slot, res_id = m.group(1), m.group(2)
        role = _slot_to_pbr_role(slot)  # albedo_texture → albedo
        if role and res_id in ext_resources:
            mappings[ext_resources[res_id]] = role

    _update_kb_from_mappings(mappings)
    return mappings
```

---

## 10. MODULO 6 — GENERATOR

**Responsabilità**: Conversioni deterministiche e tracciabili. NIENTE AI. NIENTE probabilistico.

### 10.1 Funzioni Core
```python
# Height → Normal (Sobel)
def height_to_normal(height_path, output_path, strength=1.0, convention="DX"):
    gray = cv2.imread(str(height_path), cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
    dx = cv2.Sobel(gray, cv2.CV_32F, 1, 0) * strength
    dy = cv2.Sobel(gray, cv2.CV_32F, 0, 1) * strength
    if convention == "DX":
        dy = -dy
    dz = np.sqrt(np.maximum(0, 1 - dx**2 - dy**2))
    normal = np.stack([(dx*0.5+0.5), (dy*0.5+0.5), (dz*0.5+0.5)], axis=2)
    cv2.imwrite(str(output_path), (np.clip(normal, 0, 1) * 255).astype(np.uint8))

# Height → AO (approximate ambient occlusion)
def height_to_ao(height_path, output_path):
    gray = cv2.imread(str(height_path), cv2.IMREAD_GRAYSCALE)
    blurred = cv2.GaussianBlur(gray, (21, 21), 0)
    ao = cv2.normalize(cv2.bitwise_not(blurred), None, 0, 255, cv2.NORM_MINMAX)
    cv2.imwrite(str(output_path), ao)

# Albedo → Roughness (luminance inversion — baseline)
def albedo_to_roughness(albedo_path, output_path, invert=True):
    img = cv2.imread(str(albedo_path))
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    if invert:
        gray = 1.0 - gray
    cv2.imwrite(str(output_path), (gray * 255).astype(np.uint8))

# ORM packing
def pack_orm(ao, roughness, metallic, output_path):
    packed = np.stack([
        cv2.imread(str(ao), cv2.IMREAD_GRAYSCALE),
        cv2.imread(str(roughness), cv2.IMREAD_GRAYSCALE),
        cv2.imread(str(metallic), cv2.IMREAD_GRAYSCALE)
    ], axis=2)
    cv2.imwrite(str(output_path), packed)

# Normal DX ↔ GL (inverti canale Green/Y)
def flip_normal_convention(normal_path, output_path):
    img = cv2.imread(str(normal_path))
    img[:, :, 1] = 255 - img[:, :, 1]  # Green channel flip
    cv2.imwrite(str(output_path), img)
```

### 10.2 Training Pairs Generation
```python
# Genera pairs per training AI upscale (4K → downscaled)
def generate_training_pairs(source_4k_path, output_dir):
    img_4k = Image.open(source_4k_path)
    for target_res in [2048, 1024, 512]:
        img_down = img_4k.resize((target_res, target_res), Image.LANCZOS)
        img_down.save(output_dir / f"{source_4k_path.stem}_{target_res}.png")
```

### 10.3 Provenance Obbligatoria
```python
# Ogni file generato deve scrivere il suo process.json
def write_process_record(output_file, parent_files, operation, parameters, tool_version):
    record = {
        "output": output_file.name,
        "derived_from": [str(p) for p in parent_files],
        "process": operation,
        "tool": tool_version,
        "parameters": parameters,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "input_hash": sha256(parent_files[0]),
        "output_hash": sha256(output_file)
    }
    return record
```

---

## 11. MODULO 7 — CORRELATION ENGINE

**Responsabilità**: Analizzare correlazioni fisiche tra le mappe di un set. Output: `correlations.json`.

### 11.1 Tipi di Correlazione
```python
# A — Intra-set (stesso materiale, stessa variante)
intra_set_correlations = {
    "albedo_roughness":       histogram_correlation(albedo, roughness),
    "normal_height_gradient": gradient_match_score(normal, height),
    "seamless_score":         fft_seam_analysis(albedo),
    "tiling_quality":         border_continuity_check(albedo)
}

# B — Cross-variant (stesso materiale, varianti diverse)
cross_variant = {
    "ssim_2k_vs_4k":    ssim(variant_2k, variant_4k_downscaled),
    "psnr_2k_vs_4k":    psnr(variant_2k, variant_4k_downscaled),
    "color_drift_lab":  lab_distance(variant_2k, variant_4k)
}

# C — Cross-material (materiali diversi nello stesso gruppo)
cross_material = {
    "lab_distance":     mean_lab_distance(mat_a_albedo, mat_b_albedo),
    "style_similarity": histogram_intersection(mat_a, mat_b)
}

# D — RAW vs CUSTOM (qualità della generazione)
raw_vs_custom = {
    "artifact_score":   artifact_detection_score(generated_normal),
    "ssim_generated_vs_original": ssim(generated, original) if original_exists else None
}
```

### 11.2 Physical Correlations (novità v3.0)
```python
# Correlazioni fisiche ATTESE — se mancano, segnala incoerenza
EXPECTED_PHYSICAL_CORRELATIONS = {
    ("normal", "height"):     {"correlation_min": 0.7, "reason": "normal is gradient of height"},
    ("roughness", "ao"):      {"correlation_min": 0.5, "reason": "cavities accumulate roughness"},
    ("albedo_edges", "normal"): {"correlation_min": 0.3, "reason": "visible scratches need depth"},
}

def check_physical_coherence(map_set):
    warnings = []
    for (map_a, map_b), expectations in EXPECTED_PHYSICAL_CORRELATIONS.items():
        if map_a in map_set and map_b in map_set:
            corr = calculate_correlation(map_set[map_a], map_set[map_b])
            if corr < expectations["correlation_min"]:
                warnings.append({
                    "type": f"{map_a}_{map_b}_incoherent",
                    "detected": corr,
                    "expected_min": expectations["correlation_min"],
                    "reason": expectations["reason"]
                })
    return warnings
```

---

## 12. MODULO 8 — PBR VALIDATOR (Physics Oracle)

**Responsabilità**: Validare ogni mappa contro profili fisici reali. Non blocca — segnala.

### 12.1 Physics Oracle Structure (06_KNOWLEDGE_BASE/rules/pbr_rules.json)
```json
{
  "profiles": {
    "brick_standard": {
      "albedo_srgb_range": [120, 160],
      "roughness_range": [0.7, 0.9],
      "metallic": 0,
      "specular_f0": 0.04
    },
    "metal_copper": {
      "albedo_rgb": [190, 120, 60],
      "roughness_range": [0.3, 0.6],
      "metallic": 1,
      "specular_f0_linear": [0.999, 0.900, 0.744]
    },
    "dielectric_universal": {
      "specular_f0": 0.04,
      "specular_f0_exception_wood": [0.04, 0.05]
    }
  },
  "map_rules": {
    "albedo": {
      "grayscale_forbidden": false,
      "brightness_min": 30,
      "brightness_max": 240,
      "color_space": "sRGB"
    },
    "normal": {
      "blue_channel_mean_min": 100,
      "color_space": "Linear"
    },
    "metallic": {
      "grayscale_required": true,
      "binary_expected": true,
      "binary_tolerance": 0.20
    },
    "roughness": {
      "grayscale_required": true,
      "color_space": "Linear"
    }
  }
}
```

### 12.2 Validation Levels
```python
# Level 1: Runtime (sempre attivo, mai bloccante)
def runtime_check(map_file, map_type, profile=None):
    violations = []
    rules = load_pbr_rules()[map_type]
    mean_val = np.mean(cv2.imread(str(map_file), cv2.IMREAD_GRAYSCALE))

    if mean_val < rules.get("brightness_min", 0):
        violations.append({"severity": "warning", "check": "brightness_min"})

    if rules.get("binary_expected") and not is_binary_channel(map_file):
        violations.append({"severity": "warning", "check": "metallic_non_binary"})

    return violations  # NEVER blocks

# Level 2: Pre-Export Gate (richiede conferma utente)
def pre_export_check(material_group):
    all_violations = []
    for map_type, asset in material_group.items():
        all_violations += runtime_check(asset, map_type)
    return all_violations  # mostra a UI, richiede [Export Anyway] o [Fix First]

# Level 3: Auto-Fix (OFF per default, richiede approvazione)
def auto_fix_and_export(map_file, violations, profile):
    log = []
    for v in violations:
        if v["check"] == "brightness_min" and v["severity"] == "warning":
            # clamp albedo to physical range
            img = adjust_levels(map_file, target_min=30)
            log.append(f"Clamped {map_file.name} albedo min to 30 sRGB")
    return log
```

---

## 13. MODULO 9 — P-ID MASK ENGINE

**Responsabilità**: Segmentare un materiale in zone fisiche distinte.

### 13.1 Tecniche di Segmentazione
```python
# Tecnica 1: K-Means color clustering (default)
def kmeans_segmentation(albedo_path, n_clusters=4):
    img = cv2.imread(str(albedo_path))
    z = img.reshape((-1, 3)).astype(np.float32)
    _, labels, centers = cv2.kmeans(z, n_clusters, None,
                                     (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0),
                                     5, cv2.KMEANS_PP_CENTERS)
    mask = labels.reshape(img.shape[:2])
    return mask, centers

# Tecnica 2: Otsu threshold (per materiali binari tipo brick/mortar)
def otsu_segmentation(albedo_path):
    gray = cv2.cvtColor(cv2.imread(str(albedo_path)), cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

# Tecnica 3: Multi-channel feature fusion
def feature_guided_segmentation(albedo, normal, roughness):
    # Combina albedo + gradient normal + roughness variance
    # → mask con confidence per zona
    pass
```

### 13.2 Output
```json
{
  "zones": {
    "zone_0": {
      "label": "brick",
      "coverage_percent": 70,
      "material_profile": "brick_standard",
      "mask_path": "zones/zone_0_mask.png",
      "confidence": 0.87
    },
    "zone_1": {
      "label": "mortar",
      "coverage_percent": 30,
      "material_profile": "cement_mortar",
      "mask_path": "zones/zone_1_mask.png",
      "confidence": 0.82
    }
  }
}
```

---

## 14. MODULO 10 — AI VISION ENGINE

**Responsabilità**: Caption semantica e analisi visiva avanzata. Carica modelli on-demand.

### 14.1 Lifecycle OBBLIGATORIO
```python
class AIVisionEngine:
    def __init__(self):
        self.model = None
        self.processor = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def load(self):
        if self.model is None:
            self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base").to(self.device)

    def unload(self):
        # OBBLIGATORIO: libera VRAM dopo ogni batch
        self.model = None
        self.processor = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def caption(self, image_path):
        self.load()
        # ... generate caption ...
        # NON chiamare unload() qui — il caller decide quando scaricare
```

### 14.2 Modelli Supportati
```
TIER 1 (bundled, default):    Salesforce/blip-image-captioning-base
TIER 2 (opzionale, local):    LLaVA-1.5 via Ollama
TIER 3 (roadmap):             Florence-2, custom fine-tuned su MatSynth
```

---

## 15. MODULO 11 — OLLAMA CLIENT (LLM Locale)

**Responsabilità**: Wrapper per LLM locale. Risposta SEMPRE in JSON.

### 15.1 Regole Inviolabili
```python
class OllamaClient:
    DEFAULT_MODEL = "llama3"  # da config/hardware_limits.json

    def generate(self, prompt, system="") -> dict:
        # REGOLA 1: sempre JSON
        # REGOLA 2: mai crash — fallback su errore
        # REGOLA 3: timeout gestito

        try:
            response = requests.post(f"{self.host}/api/generate",
                json={"model": self.model, "prompt": prompt,
                      "system": system, "stream": False},
                timeout=120)
            raw = response.json().get("response", "")

            # Estrai JSON anche se avvolto in testo
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end != -1:
                return json.loads(raw[start:end+1])

        except Exception as e:
            logger.warning(f"Ollama unavailable: {e}")

        return {"error": "ollama_unavailable", "fallback": True}

# USO TIPICO:
# ollama.generate("Classifica questo materiale PBR. Rispondi solo JSON.")
# → {"material_type": "stone", "technique": "photogrammetry", "tags": ["worn", "outdoor"]}
```

---

## 16. MODULO 12 — KNOWLEDGE PROCESSOR (SSOT Management)

**Responsabilità**: Gestire e aggiornare la Knowledge Base da fonti esterne.

### 16.1 Fonti Integrate
```python
KNOWLEDGE_SOURCES = {
    "ambientcg_api": {
        "url": "https://ambientcg.com/api/v3/assets",
        "type": "rest_api",
        "extracts": ["tags", "technique", "category", "description"]
    },
    "physicallybased_api": {
        "url": "https://api.physicallybased.info/v2",
        "github_fallback": "AntonPalmqvist/physically-based-api",
        "extracts": ["F0_linear", "IOR", "density", "roughness_range"]
    },
    "matsynth_hf": {
        "repo": "gvecchio/MatSynth",
        "streaming": True,
        "extracts": ["material_params", "ground_truth_ranges"]
    },
    "texverse_hf": {
        "repo": "YiboZhang2001/TexVerse",
        "streaming": True,
        "extracts": ["cross_material_correlations"]
    },
    "ior_database": {
        "type": "static_csv",
        "path": "06_KNOWLEDGE_BASE/sources/csv/ior_database.csv",
        "extracts": ["IOR", "complex_n", "complex_k"]
    }
}
```

### 16.2 Knowledge Update Flow
```python
# Quando nuovi pattern vengono appresi dall'Analyzer
def update_naming_patterns(new_mappings: dict):
    kb_path = "06_KNOWLEDGE_BASE/mappings/naming_map.json"
    kb = load_json(kb_path)
    for filename, map_type in new_mappings.items():
        suffix = "_" + Path(filename).stem.split("_")[-1]
        kb["map_patterns"].setdefault(map_type.lower(), [])
        if suffix not in kb["map_patterns"][map_type.lower()]:
            kb["map_patterns"][map_type.lower()].append(suffix)
    save_json(kb_path, kb)  # atomic write
    NamingIntelligence.reload_kb()  # hot reload
```

---

## 17. MODULO 13 — DATASET BUILDER

**Responsabilità**: Assemblare output finale AI-ready da tutti i processed manifests.

### 17.1 Output Formats
```python
# master.json — runtime light (per DVAMOCLES SWORD™ runtime)
{
  "materials": [
    {
      "id": "Tiles_138",
      "provider": "AmbientCG",
      "technique": "Photogrammetry",
      "tags": ["tiles", "stone"],
      "maps": {"albedo": "path", "normal": "path", "roughness": "path"},
      "physics_profile": "stone_ceramic",
      "pbr_complete": true
    }
  ]
}

# raw.json — training complete (per addestrare modelli AI)
{
  "materials": [
    {
      "id": "Tiles_138",
      # ... tutto il master +
      "process_history": [...],
      "correlations": {...},
      "physics_validation": {...},
      "pid_zones": {...},
      "ai_captions": {...},
      "training_pairs": [...]
    }
  ]
}
```

### 17.2 SQLite Index
```sql
CREATE TABLE materials (
    id TEXT PRIMARY KEY,
    provider TEXT,
    technique TEXT,
    pbr_complete INTEGER,
    physics_compliance REAL,
    variant_count INTEGER,
    file_count INTEGER,
    import_date TEXT
);

CREATE TABLE map_files (
    id TEXT PRIMARY KEY,
    material_id TEXT,
    variant TEXT,
    map_type TEXT,
    resolution TEXT,
    format TEXT,
    path TEXT,
    confidence REAL,
    FOREIGN KEY (material_id) REFERENCES materials(id)
);
```

---

## 18. PIPELINE ORCHESTRATOR — SEQUENZA COMPLETA

```python
class PipelineOrchestrator:
    def run(self, project_payload=None, skip_import=False):
        stages = {}

        # FASE 1 — CORE (obbligatoria)
        if not skip_import:
            stages["import"] = ImportAssistant.run(project_payload)
        stages["ingestion"] = Ingestor.run_full()
        stages["metadata"] = MetadataExtractor.enrich_all()
        stages["naming"] = NamingIntelligence.classify_all()

        # FASE 2 — PROCESSING
        stages["generation"] = Generator.fill_missing_maps()
        stages["validation"] = PBRValidator.process_all()

        # FASE 3 — ANALYSIS
        stages["correlation"] = CorrelationEngine.run()
        stages["pid_masks"]   = PIDMaskEngine.run()

        # FASE 4 — AI (opzionale, skip se AI non disponibile)
        if ai_available():
            stages["ai_vision"] = AIVisionEngine.caption_all_albedo()
            AIVisionEngine.unload()  # OBBLIGATORIO

        # FASE 5 — OUTPUT
        stages["knowledge"] = KnowledgeProcessor.run()
        stages["dataset"]   = DatasetBuilder.run()
        stages["qa_gates"]  = KnowledgeBaseQualityGates.run()

        # Event
        EventBus.publish("pipeline.completed", {"stages": stages})
        return stages
```

---

## 19. USER INTERACTION FLOWS

### 19.1 Flow A — Drag & Drop Import (percorso principale)

```
UTENTE                          SISTEMA
──────────────────────────────────────────────────────────────────
Trascina cartella/zip su GUI
                                → Staging area creata (uuid)
                                → File enumerati + filtrati
                                → Detection Stack eseguito:
                                  • ExifTool metadata
                                  • OpenCV visual classify
                                  • NID filename match
                                  • MaterialX sidecar check
                                → ProposedGroups generati

                                ANALYZER UI appare:
                                ┌─────────────────────────────────┐
                                │ THE ANALYZER                    │
                                │ ─────────────────────────────── │
                                │ [thumb] Rock_BC.png             │
                                │         Albedo ●95%  sRGB  ✓   │
                                │ [thumb] Rock_N.png              │
                                │         Normal ●98%  Lin   ✓   │
                                │ [thumb] Rock_ORM.png            │
                                │         ORM Packed ●87% ─── ✓  │
                                │           R→AO G→R B→M          │
                                │ [thumb] img_01.jpg              │
                                │         Unknown ●12%  ???  ⚠   │
                                │                                 │
                                │ Proposed: [Rock_01 — 3 files]   │
                                │           [Ungrouped: img_01]   │
                                │                    [Confirm →]  │
                                └─────────────────────────────────┘

Corregge img_01 → map_type "Height"
Approva gruppi
Clicca [Confirm →]
                                → Copia in 01_RAW_ARCHIVE/
                                → Scrive material_info.json
                                → Pubblica "import.completed"
                                → Trigger automatico Ingestor
                                → Progress indicator in UI
                                → Toast: "Rock_01 importato. 3 mappe. ✓"
```

### 19.2 Flow B — EXECUTE FORGE (import + full pipeline)

```
UTENTE                          SISTEMA
──────────────────────────────────────────────────────────────────
Clicca [EXECUTE FORGE]
(dopo aver configurato materiali
 nell'inspector)
                                → Pipeline Orchestrator avviato
                                → Worker Thread (non blocca UI)

                                PROGRESS (bottom bar):
                                [IMPORT] ████░░░░ 40%
                                "Copiando Rock_01 in RAW..."

                                [INGEST] ████████ 100% ✓
                                [METADATA] ████████ 100% ✓
                                [GENERATE] ████░░░░ 50%
                                "Generando Normal da Height..."

                                [VALIDATE] ████████ 100% ✓
                                ⚠ Rock_01: roughness sotto range (0.61 < 0.70)

                                [DATASET] ████████ 100% ✓

                                TOAST RESULT:
                                "Forge completato
                                 Materiali: 3 | File: 15 | Maschere: 6
                                 ⚠ 1 warning PBR — clicca per dettagli"

Clicca warning
                                → Inspector mostra physics_validation.json
                                → Offre: [Export Anyway] [Auto-Fix] [Fix Manual]
```

### 19.3 Flow C — Knowledge Update (AmbientCG + PhysicallyBased)

```
UTENTE                          SISTEMA
──────────────────────────────────────────────────────────────────
Workspace "Knowledge"
Clicca [Provider Info → AmbientCG]
Inserisce asset ID "Tiles138"
                                → API call: ambientcg.com/api/v3/assets?id=Tiles138
                                → Fetch metadata: title, tags, downloads list
                                → Salva in 06_KNOWLEDGE_BASE/sources/api/
                                → Toast: "Metadata AmbientCG salvati"

Clicca [Provider Info → PhysicallyBased]
Clicca [Import da GitHub]
                                → Clone/fetch: physically-based-api/main/data/
                                → Parse materials.json, lightsources.json
                                → Aggiorna pbr_rules.json con F0 reali
                                → Pubblica "knowledge.updated"
                                → Toast: "89 materiali fisici aggiornati"

Workspace "Dataset"
Clicca [Rigenera Dataset]
                                → DatasetBuilder.run() in background
                                → Aggiorna master.json + raw.json + database.db
                                → Lista file 04_DATASET/ si aggiorna in UI
```

### 19.4 Flow D — Bulk Import AmbientCG

```
UTENTE                          SISTEMA
──────────────────────────────────────────────────────────────────
Clicca [AmbientCG ALL]
Inserisce batch_size: 20
                                → Chiede: resume sessione precedente? (se stato salvato)

Clicca [Resume]
                                → Carica bulk_resume_state.json
                                → Continua da offset salvato

                                PROGRESS WINDOW:
                                ┌─────────────────────────┐
                                │ AmbientCG Bulk Import   │
                                │ Downloading Rock035...  │
                                │ [████████░░] 156/300    │
                                └─────────────────────────┘

                                Per ogni asset:
                                → download_all_variants() → tutte le ZIP
                                → Estrai in temp/staging_web/{asset_id}/
                                → Crea asset_context.json (provider metadata)
                                → Salva resume state ogni asset

In caso di crash/stop
                                → Resume state preservato
                                → Riprendere da dove si era fermati

Completato
                                → Toast: "AmbientCG Import: 156 asset estratti"
                                → Auto-sort in staging → Vault
```

### 19.5 Flow E — Pipeline Reports Only (headless)

```bash
# CLI headless — salta import, esegue solo elaborazione
python main_pipeline.py --reports-only

# Output in /06_KNOWLEDGE_BASE/reports/pipeline_run_report.json
{
  "status": "success",
  "stages": {
    "ingestion":   {"status": "ok", "processed": 45, "errors": 0},
    "validation":  {"status": "partial", "warnings": 3},
    "dataset":     {"status": "ok", "variants": 120}
  }
}
```

---

## 20. EXTERNAL INTEGRATIONS COMPLETE REFERENCE

### 20.1 AmbientCG REST API
```python
BASE_URL = "https://ambientcg.com/api/v3/assets"

# Search
GET /assets?q=stone&type=material&limit=25&include=title,downloads,tags

# Single asset
GET /assets?id=Tiles138&type=material&include=title,downloads

# Catalog paginated
GET /assets?q=&type=material&limit=20&offset=40&sort=popular

# Response structure:
{
  "assets": [
    {
      "id": "Tiles138",
      "title": "Tiles 138",
      "dataType": "Material",
      "tags": ["tiles", "stone"],
      "downloads": [
        {
          "extension": "zip",
          "attributes": "2K-PNG",
          "url": "https://ambientcg.com/get?file=Tiles138_2K-PNG.zip"
        }
      ]
    }
  ],
  "totalResults": 4521
}

# Rate limits: rispetta con sleep(0.5) tra richieste
# Cache zip in temp/cache/ambientcg/{asset_id}_{variant}.zip
```

### 20.2 PhysicallyBased API
```python
API_BASE = "https://api.physicallybased.info/v2"
GITHUB_RAW = "https://raw.githubusercontent.com/AntonPalmqvist/physically-based-api/main/data"

# Endpoints
GET /v2/materials       → lista materiali con F0, IOR, density
GET /v2/lightsources    → sorgenti luminose
GET /v2/cameras         → dati camera fisici

# GitHub fallback (se API offline)
GET {GITHUB_RAW}/materials.json
GET {GITHUB_RAW}/lightsources.json

# Response item structure:
{
  "name": "Copper",
  "type": "Metal",
  "baseColor": [0.932, 0.623, 0.522],
  "specularF0": [0.999, 0.900, 0.744],
  "ior": 1.10,
  "density": 8940
}
```

### 20.3 Hugging Face Datasets
```python
from datasets import load_dataset

# MatSynth — 4000+ materiali PBR 4K CC0
ds = load_dataset("gvecchio/MatSynth", streaming=True)
# Campi: basecolor, normal, roughness, metalness, height, ao, material_type, tags

# TexVerse — 858K modelli 3D con materiali PBR
ds = load_dataset("YiboZhang2001/TexVerse", streaming=True, split="train")

# Uso con streaming (evita OOM su dataset grandi)
for sample in ds:
    process_sample(sample)
    # Non caricare tutto in RAM

# DVC per versionare dataset grandi
# dvc add 01_RAW_ARCHIVE/
# → crea 01_RAW_ARCHIVE.dvc (committabile in Git)
```

### 20.4 Ollama (LLM Locale)
```python
# Installazione: https://ollama.ai
# Windows: winget install Ollama.Ollama
# Modelli: ollama pull llama3 / ollama pull mistral / ollama pull gemma3

HOST = "http://127.0.0.1:11434"  # da config/hardware_limits.json

# API
POST /api/generate
{
  "model": "llama3",
  "prompt": "...",
  "system": "Rispondi SOLO in JSON valido.",
  "stream": false
}

# Verificare disponibilità
GET /api/tags → lista modelli installati

# FALLBACK OBBLIGATORIO: se Ollama offline, ritorna dict di errore
# NEVER crash l'applicazione per LLM non disponibile
```

### 20.5 ExifTool
```python
# Portabile: metti exiftool.exe in /exiftool_files/
# PATH fallback: shutil.which("exiftool")

# Comando standard
subprocess.run(["exiftool", "-j", "-G", str(file_path)],
               capture_output=True, text=True)

# Output JSON:
[{
  "File:ImageWidth": 2048,
  "File:ImageHeight": 2048,
  "PNG:BitDepth": 8,
  "ICC_Profile:ProfileDescription": "sRGB IEC61966-2.1",
  "PNG:Software": "Adobe Photoshop CC 2024"
}]
```

### 20.6 MaterialX
```python
# pip install MaterialX

import MaterialX as mx

doc = mx.createDocument()
mx.readFromXmlFile(doc, str(mtlx_path))

# Itera nodi per mapping file→map_type
for nodegraph in doc.getNodeGraphs():
    for node in nodegraph.getNodes():
        for input_ in node.getInputs():
            if input_.getType() == "filename":
                file = input_.getValue()  # "texture_albedo.png"
                role = node.getCategory()  # "tiledimage", "image"
                # → mappings[Path(file).name] = _role_to_canonical(role)

# MaterialX ha PRIORITÀ MASSIMA su NID
# Se .mtlx esiste → usa quei mapping, NID è fallback
```

### 20.7 DVC (Data Version Control)
```bash
# Setup iniziale
pip install dvc
dvc init

# Track dataset pesante
dvc add 01_RAW_ARCHIVE/
git add 01_RAW_ARCHIVE.dvc .gitignore
git commit -m "Track RAW archive with DVC"

# Storage remoto (opzionale)
dvc remote add -d myremote s3://my-bucket/dvc
dvc push

# Pull su altra macchina
dvc pull

# Vantaggi: Git traccia solo puntatori .dvc, DVC gestisce i file grandi
```

---

## 21. ERROR HANDLING POLICY

```python
# REGOLA 1: Never crash
try:
    result = risky_operation()
except Exception as e:
    logger.error(f"[MODULE_NAME] {e}", exc_info=True)
    result = {"status": "error", "fallback": True, "error": str(e)}
    EventBus.publish("module.error", {"module": "MODULE_NAME", "error": str(e)})

# REGOLA 2: Fallback sempre disponibile
def extract_metadata(file_path):
    # Try 1: ExifTool (più completo)
    result = exiftool_extract(file_path)
    if result:
        return result
    # Try 2: Pillow (fallback)
    result = pillow_extract(file_path)
    if result:
        return result
    # Try 3: OpenCV (ultimo resort)
    return opencv_extract(file_path)

# REGOLA 3: Log tutto
# Log file: logs/last_session.log (sovrascritta ogni sessione)
# Rotazione: max 5 file (session_1.log → session_5.log)
# Format: "TIMESTAMP | LEVEL | MODULE | message"

# REGOLA 4: Staging area isolation
# Se staging fallisce → staging_dir viene rimossa
# RAW Archive non viene mai toccato in caso di errore
```

---

## 22. PRIORITY IMPLEMENTAZIONE — ORDINE DI BUILD

```
FASE 1 — CORE FONDAMENTA (senza questo niente funziona)
  ✅ AppStateManager + valid transitions
  ✅ EventBus (asyncio pub/sub)
  ✅ 06_KNOWLEDGE_BASE/ setup con naming_map.json e pbr_rules.json
  ✅ NamingIntelligence (legge da KB, zero hardcode)
  ✅ MetadataExtractor (ExifTool + Pillow fallback)
  ✅ ImportAssistant base (staging + detection + confirm)
  ✅ Ingestor (grouping + variant detection + manifest)

FASE 2 — PROCESSING
  ✅ Generator (height→normal, AO, ORM packing)
  ✅ PBRValidator (physics oracle + soft-gate)
  ✅ UniversalParser (.mtlx + .tres)

FASE 3 — ANALYSIS
  ✅ CorrelationEngine (intra-set + cross-variant)
  ✅ PIDMaskEngine (K-Means + Otsu)
  ✅ DatasetBuilder (master.json + raw.json + SQLite)

FASE 4 — INTEGRAZIONI ESTERNE
  ✅ AmbientCGFetcher (search + download_all_variants + bulk)
  ✅ PhysicallyBasedFetcher (API + GitHub fallback)
  ✅ KnowledgeProcessor (HF datasets + KB update)
  ✅ DVC setup

FASE 5 — AI (opzionale, graceful degradation se non disponibile)
  ✅ AIVisionEngine (BLIP caption, on-demand load/unload)
  ✅ OllamaClient (JSON-only, always fallback)

FASE 6 — GUI
  ✅ Analyzer UI (mostra detection, confidence, correction)
  ✅ Pipeline progress (Worker Thread + progress indicators)
  ✅ Workspace Blender-style (Import/Vault/Inspect/Dataset/Knowledge/Pipeline)
```

---

## 23. CRITICAL ANTI-PATTERNS — NON FARE MAI

```python
# ❌ SBAGLIATO: Logica naming hardcoded
MAP_PATTERNS = {"_BC": "albedo", "_N": "normal"}  # VIETATO in Python

# ✅ CORRETTO: Da knowledge base
patterns = json.load(open("06_KNOWLEDGE_BASE/mappings/naming_map.json"))

# ❌ SBAGLIATO: Modificare RAW Archive
shutil.copy(processed_file, raw_archive_path)  # VIETATO

# ✅ CORRETTO: Scrivere in CUSTOM con provenance
shutil.copy(generated_file, custom_path)
write_process_json(generated_file, parent=original, operation="height_to_normal")

# ❌ SBAGLIATO: AI muta stato direttamente
def ai_suggest(texture):
    apply_correction(texture)  # VIETATO

# ✅ CORRETTO: AI produce suggestion object, Command Pattern applica
def ai_suggest(texture):
    return {"suggestion": "adjust_roughness", "value": 0.85}
# Il Command Pattern decide se applicare

# ❌ SBAGLIATO: Crash su Ollama/AI offline
result = ollama.generate(prompt)  # se Ollama offline → Exception → crash

# ✅ CORRETTO: Sempre fallback
result = ollama.generate(prompt) or {"error": "offline", "fallback": True}

# ❌ SBAGLIATO: Pattern duplicati (Python + YAML + JSON)
# naming_intelligence.py ha MAP_PATTERNS hardcoded
# config/pipeline_config.yaml ha naming.vendor_patterns
# 06_KNOWLEDGE_BASE/mappings/naming_map.json ha map_patterns
# → 3 sorgenti conflittuali = caos totale

# ✅ CORRETTO: UN SOLO posto
# 06_KNOWLEDGE_BASE/mappings/naming_map.json è l'UNICA fonte
# Python carica, YAML non contiene pattern, Python ha solo fallback se file mancante

# ❌ SBAGLIATO: Main entry point ambiguo
# main.py → SentinelPipeline class inline
# Run_pipeline.py → core/pipeline.py wrapper
# → due runner con architetture diverse → output diversi

# ✅ CORRETTO: Un solo canonical entry point
# main_pipeline.py → core/pipeline_orchestrator.py (CANONICAL)
# main_gui.py → GUI wrapper che chiama pipeline_orchestrator
```

---

## 24. TESTING — MINIMUM FUNCTIONAL CORE

Il sistema è considerato funzionante quando questo flow end-to-end passa senza errori:

```
STEP 1:  Utente avvia applicazione → SplashScreen → Project Hub
STEP 2:  Crea nuovo progetto (nome + path)
STEP 3:  Trascina cartella con 3 texture (BC.png, N.png, ORM.png)
STEP 4:  Analyzer mostra: 3 file, grouping suggerito, confidence ≥ 0.80
STEP 5:  Utente conferma
STEP 6:  Material Group appare in Library con Glow System attivo
STEP 7:  Utente trascina gruppo in Workspace
STEP 8:  Auto-pipeline: ORM Unpack + PBR Validate
STEP 9:  PBR badge verde ✓
STEP 10: Export Panel → seleziona UE5_2K profile → [Export]
STEP 11: /ExportRoot/UE5/Rock_01/ creata con:
         T_Rock_01_BC.tga  ✓
         T_Rock_01_N.tga   ✓
         T_Rock_01_ORM.tga ✓
         MaterialReport_Rock_01_UE5.txt ✓
STEP 12: Aggiungi Unity_URP_2K profile → [Export All]
STEP 13: /ExportRoot/Unity_URP/Rock_01/ creata con:
         Rock_01_Albedo.png   ✓ (GL normal convention)
         Rock_01_Normal.png   ✓ (G channel flipped)
         Rock_01_RMA.png      ✓
```

---

## 25. .CURSORRULES — COPIA QUESTO FILE IN PROJECT ROOT

```text
# .cursorrules — DVAMOCLES SWORD™: SIGNUM SENTINEL v3.0

## Ruolo
Sei un assistente senior per Python 3.12 che implementa la pipeline SIGNUM SENTINEL.
Leggi SEMPRE SIGNUM_SENTINEL_CURSOR_BUILD_PROMPT.md prima di rispondere.

## Architettura — Non Negoziabile
- Event Bus: nessun modulo muta stato globale direttamente, emette eventi
- Command Pattern: ogni mutazione è un Command atomico
- Worker Thread: UI non si blocca mai
- AI isolation: AI riceve snapshot, non muta mai stato

## Filesystem — Hard Rules
- 01_RAW_ARCHIVE/ → READ ONLY assoluto. Zero scritture.
- 02_CUSTOM/ → ogni file derivato DEVE avere process.json con parent + operations + hash
- 06_KNOWLEDGE_BASE/ → SSOT per naming e physics. Logica nei JSON, mai in Python.

## Naming Intelligence
- naming_map.json è l'UNICA fonte. Zero hardcode in Python.
- NamingIntelligence.__init__ deve caricare da KB, hardcode solo come fallback se file mancante

## AI Modules
- Tutti i modelli HuggingFace: carica on-demand, rilascia dopo uso (gc.collect + cuda.empty_cache)
- Ollama: risponde SEMPRE dict, mai crash, always fallback
- AI non muta mai stato direttamente — produce suggestion objects

## Moduli — Responsabilità Singola
- ImportAssistant → staging + detection + gating
- MetadataExtractor → solo ExifTool/Pillow metadata
- VisualAnalyzer → solo OpenCV pixel-level
- NamingIntelligence → solo filename → map_type da KB
- Generator → solo conversioni deterministiche (zero AI)
- CorrelationEngine → metriche (SSIM, PSNR, histogram, FFT)
- PBRValidator → confronto Physics Oracle
- DatasetBuilder → JSON/SQLite finali

## Provenance (Critico per dataset)
Ogni file in 02_CUSTOM/ deve avere record con:
  parent, operations, parameters, tool+version, timestamp, input_hash_sha256, output_hash_sha256

## Error Handling
- Never crash — sempre fallback
- Log tutto in logs/last_session.log
- Rotazione max 5 file (session_1..session_5)

## Entry Point Canonico
- Pipeline headless: main_pipeline.py → core/pipeline_orchestrator.py
- GUI: main_gui.py → chiama pipeline_orchestrator (non inline)
- NON duplicare logica tra i due

## Come rispondere
- "Implementa X" → lavora nel modulo appropriato in core/
- "Aggiungi integrazione Y" → KnowledgeProcessor o ImportAssistant
- "Refactor" → mantieni API pubbliche usate da main_gui.py e main_pipeline.py
- NON spostare/rinominare moduli senza motivazione esplicita
- NON duplicare logica tra moduli (segnala se stai per farlo)
- NON riscrivere architettura — estendi i punti di extension esistenti
```

---

## 26. CONFIGURAZIONE FILES DI AVVIO

### config/hardware_limits.json
```json
{
  "gpu_memory_fraction": 0.5,
  "max_parallel_jobs": 2,
  "max_texture_resolution_ai": 2048,
  "ollama_model": "llama3",
  "ollama_host": "http://127.0.0.1:11434",
  "ollama_auto_stop": true,
  "blip_auto_unload_after_n_images": 20,
  "exiftool_batch_size": 50
}
```

### config/pipeline_config.json
```json
{
  "schema_version": "1.0.0",
  "raw_readonly": true,
  "dataset_output_dir": "04_DATASET",
  "correlations_append_only": true,
  "generator_supports_packed_schemes": ["ORM", "ARM", "RMA"],
  "ai_vision_enabled": true,
  "ollama_enabled": true,
  "dvc_enabled": false,
  "export_formats": ["UE5", "Unity_URP", "Unity_HDRP", "Godot"],
  "staging_cleanup_after_confirm": true
}
```

### requirements.txt (completo)
```txt
# UI
customtkinter>=5.2.0
tkinterdnd2>=0.3.0
psutil>=5.9.0

# Imaging
Pillow>=10.0.0
opencv-python>=4.8.0
numpy>=1.24.0

# Metadata
pyexiftool>=0.5.6

# AI Vision
torch>=2.1.0
torchvision>=0.16.0
transformers>=4.35.0
accelerate>=0.26.0
safetensors>=0.4.0
huggingface_hub>=0.20.0

# Datasets
datasets>=2.16.0

# MaterialX
MaterialX>=1.38.0

# HTTP / APIs
requests>=2.31.0
beautifulsoup4>=4.12.0

# Data
pydantic>=2.0.0

# Optional: LLM
# ollama  # install separately: https://ollama.ai

# Optional: DVC
# dvc>=3.0.0

# Build / deploy
pyinstaller>=6.0.0
pywin32>=306  # Windows only
```

---

## 27. STATO ATTUALE DEL CODEBASE (PROBLEMI NOTI DA RISOLVERE)

Questi problemi esistono nel codebase attuale (da Report Tecnico 2026-04-24):

```
🔴 CRITICO-1: naming_intelligence.py ha MAP_PATTERNS hardcoded — non legge da KB
   Fix: __init__ accetta mappings_path, carica da naming_map.json, hardcode come fallback

🔴 CRITICO-2: 4 file Oracle duplicati (materials_dielectrics.json, dielectrics.json, etc.)
   Fix: elimina oracle/dielectrics.json e oracle/metals.json (duplicati non usati)

🔴 CRITICO-3: Due entry point concorrenti (main.py vs Run_pipeline.py)
   Fix: main_pipeline.py → core/pipeline_orchestrator.py è CANONICAL
        main.py diventa legacy/deprecated

🔴 CRITICO-4: import_assistant material_info.json manca source_url, tags, technique, category
   Fix: estendi _write_material_info() con campi §4.1 schema completo

🔴 CRITICO-5: _write_process_json ha break nel loop (scrive solo 1 entry invece di N)
   Fix: rimuovi break, crea entry per ogni file processato

🟡 STRUCT-1: Sintassi list[str] / dict[str, ...] (Python 3.9+)
   Fix: aggiungi "from __future__ import annotations" ai moduli affetti

🟡 STRUCT-2: 02_CUSTOM/ ha output senza material_info.json / process.json
   Fix: Normalizer deve chiamare write_material_info() quando scrive in CUSTOM

🟡 STRUCT-3: variant_generator.py e asset_parser.py non integrati nel pipeline flow
   Fix: agganciare in PipelineOrchestrator (Fase 3)
```

---

*Documento: SIGNUM SENTINEL v3.0 — Cursor Build Prompt*
*Generato: 2026-04-27 | Autorità: DVAMOCLES_3.1-FINAL + SENTINEL_SPEC_v3 + Git Analysis*
*Feed questo file + DVAMOCLES_3.1-FINAL_EN_AI-Ready.md a Cursor come context permanente*
