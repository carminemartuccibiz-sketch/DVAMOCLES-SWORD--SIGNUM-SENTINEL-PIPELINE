# DVAMOCLES SWORD™: Material Forge Studio®
## SIGNUM SENTINEL — Dataset & Intelligence Protocol v3.0
**Data: 2026-04-20 | Sostituisce: Dataset Protocol v2.0**
**Fonti: v1.0 + v2.0 + PBR_MKB_ParteA/B/C + Physically Based Database + IOR Data + Note tecniche sessione**

---

## 0. RIPOSIZIONAMENTO STRATEGICO

### 0.1 Cos'è SIGNUM SENTINEL

SIGNUM SENTINEL non è uno script di elaborazione texture. È il **cervello di DVAMOCLES SWORD™** — nella sua forma attuale, funge da sistema di sviluppo interno; nella sua forma definitiva, sarà l'intelligenza artificiale embedded nel software.

La pipeline descritta in questo documento è simultaneamente tre cose:

1. **Dataset Factory** — produce dati strutturati per addestrare l'AI
2. **Material Physics Engine** — valida e corregge materiali usando conoscenza fisica reale
3. **Foundation di Sentinel** — il sistema che diventerà l'AI del software DVAMOCLES

Il dataset che costruiamo oggi è il corpus di addestramento di Sentinel. Le decisioni che prendiamo ora su come strutturare, classificare e analizzare i materiali diventano le "leggi fisiche" che Sentinel applicherà agli asset degli utenti finali.

### 0.2 Il Physics Oracle

Al centro del sistema c'è una novità architetturale rispetto alla v2: il **Physics Oracle** — un layer di conoscenza fisica di riferimento costruito a partire dalle banche dati integrate:

- **PBR Master Knowledge Base** (Parti A, B, C) — fondamenti fisici, formule BRDF, range validati
- **Physically Based Database** (physicallybased.info) — F0 misurati per 80+ materiali, densità, luminanza
- **IOR Database** (CGSociety + SpectralDB) — indici di rifrazione per 200+ materiali
- **Lista valori BaseColor/Albedo Metalli** — range sRGB validati per workflow Metal/Roughness
- **MaterialX / OpenPBR mappings** — connessione tra parametri fisici e formato standard
- **Articoli e studi di settore** — in crescita continua, integrati man mano

Il Physics Oracle non è un modulo che esegue calcoli al volo. È un **database di riferimento** contro cui ogni materiale viene confrontato. Cresce con la ricerca e aggiorna automaticamente i threshold del Validator.

---

## 1. ARCHITETTURA AGGIORNATA — 4 LAYER

```
┌─────────────────────────────────────────────────────────────┐
│         LAYER 0 — PHYSICS ORACLE (Knowledge Base)           │
│  IOR Database · F0 Profiles · Albedo Ranges · MaterialX     │
│  SpectralDB · OpenPBR mappings · Articoli di settore        │
│  → riferimento immutabile, aggiornato manualmente           │
│  → consultato da tutti gli altri layer                      │
├─────────────────────────────────────────────────────────────┤
│         LAYER 1 — DETERMINISTIC CORE                        │
│  Ingestor · Naming Intelligence · Metadata Extractor        │
│  Normalizer · Physics Validator · Cross-Map Analyzer        │
│  Scale Estimator · Tiling Analyzer · Coherence Checker      │
│  → matematica pura, risultati riproducibili al 100%         │
│  → usa Physics Oracle come reference, non come AI           │
├─────────────────────────────────────────────────────────────┤
│         LAYER 2 — SEMANTIC AI                               │
│  AI Analyzer (LLaVA) · Damage Detector                      │
│  SAM PID Generator · Material Classifier                    │
│  Cross-Material Comparator · Variant Generator              │
│  → arricchimento semantico, mai sovrascrive Layer 1         │
│  → usa Physics Oracle per contestualizzare le analisi       │
├─────────────────────────────────────────────────────────────┤
│         LAYER 3 — DECISION + SYNTHESIS ENGINE               │
│  Decision Layer · Coherent Edit Propagator                  │
│  Multi-Material Blending Advisor · Dataset Builder          │
│  → converte analisi in azioni · assembla output finale      │
└─────────────────────────────────────────────────────────────┘
```

**Regola fondamentale invariata:** ogni layer legge il layer inferiore ma non lo sovrascrive. Layer 0 è immutabile (solo aggiornamenti manuali deliberati).

---

## 2. SISTEMA DI CLASSI DATI (invariato da v2, esteso)

Ogni dato porta obbligatoriamente:
```json
{
  "class": "...",
  "source": "...",
  "confidence": 0.0,
  "physics_validated": false
}
```

Il nuovo campo `physics_validated` indica se il dato è stato confrontato contro il Physics Oracle.

| Classe | Descrizione | Uso | Note |
|---|---|---|---|
| **GOLD** | Originali non alterati, verificati | Training principale, ground truth | MAI modificati |
| **DERIVED** | Algoritmi deterministici | Training secondario | Affidabili, non ground truth |
| **SYNTHETIC** | AI generativa | Augmentation, robustness | MAI ground truth |
| **REFERENCE** | Foto reali utente | Training comportamento fisico | Appendice D |
| **ANALYSIS** | Metriche estratte | Feature engineering | Non immagini |
| **MASK** | Segmentazioni | P-ID, damage, zone fisiche | Output SAM + LLaVA |
| **LABEL** | Semantica interpretata | Classificazione, NID | Confidence obbligatoria |
| **PHYSICS_REF** | Dati dal Physics Oracle | Validazione, benchmark | Read-only, provenienza database |

---

## 3. LAYER 0 — PHYSICS ORACLE

### 3.1 Struttura del Knowledge Base

Il Physics Oracle è un insieme di file JSON/CSV strutturati, compilati manualmente da fonti validate. Non viene modificato dal processing automatico — solo da decisioni deliberate dell'architetto.

```
PHYSICS_ORACLE/
├── materials/
│   ├── metals.json           ← F0 RGB (lineare), densità, luminanza relativa
│   ├── dielectrics.json      ← albedo sRGB range, roughness range, IOR, F0
│   ├── organics.json         ← pelle (6 toni), legno (specie), tessuti
│   └── special.json          ← nacre, car paint, SSS materials, anodizzati
├── ior_database.json         ← 200+ materiali, IOR per CGSociety + SpectralDB
├── spectral_data/            ← misurazioni SpectralDB per materiale
├── materialx_mappings/       ← OpenPBR / Substrate parameter mappings
├── pbr_rules.json            ← regole di validazione con soglie e severità
└── cross_material_patterns/  ← come due materiali si integrano fisicamente
```

### 3.2 Profili Fisici Integrati (da Physically Based Database)

Ogni materiale nel Physics Oracle ha questo schema:

```json
{
  "material_id": "PHYS_copper",
  "class": "physics_ref",
  "source": "physicallybased.info + PBR_MKB_ParteA",

  "base_color_f0_linear": [0.932, 0.623, 0.522],
  "specular_f0_linear":   [0.999, 0.900, 0.744],
  "specular_f82_linear":  [0.982, 0.947, 0.945],
  "metallic": 1,
  "density_kg_m3": 8940,
  "relative_luminance": 0.681,

  "albedo_srgb_range": {
    "min": [220, 140, 110],
    "max": [255, 220, 190],
    "notes": "warm reddish tint, R >> G > B"
  },

  "roughness_range": {
    "clean_polished": [0.05, 0.15],
    "standard": [0.30, 0.60],
    "worn_oxidized": [0.55, 0.85]
  },

  "normal_characteristics": {
    "micro_detail": "granular crystalline structure",
    "macro_variation": "low for polished, high for hammered",
    "frequency_profile": "medium-high"
  },

  "ior": 1.10,
  "ior_complex_n": 0.64,
  "ior_complex_k": 2.62,

  "physical_tags": ["metal", "conductor", "warm_tint", "recyclable"],
  "pbr_workflow": "metalness",
  "sss": false,

  "validation_rules": [
    {
      "check": "metallic_value",
      "expected": 1,
      "tolerance": 0.05,
      "severity": "error"
    },
    {
      "check": "albedo_mean_r_greater_than_b",
      "expected": true,
      "severity": "warning",
      "message": "Copper should have R >> B in Base Color"
    }
  ],

  "cross_material_notes": {
    "oxidized_copper": "Metallic drops toward 0 in oxidized zones; albedo shifts green-blue (patina)",
    "copper_on_stone": "Edge bleeding typical, IOR mismatch at boundary"
  }
}
```

### 3.3 Regole di Validazione Fisica Avanzate (da PBR_MKB)

Il Physics Oracle estende le validazioni base della v2 con confronti fisici reali:

**Albedo validation per tipo materiale:**
```
DIELETTRICI COMUNI (non-metal):
  Range operativo:    50–240 sRGB (strict)
  Range tolerant:     30–240 sRGB
  Sotto 30 sRGB:      solo carbone, pneumatici, MIT Black → flag con materiale atteso
  Sopra 240 sRGB:     solo neve, Spectralon → flag con materiale atteso
  Regola energia:     albedo + specular non superano 1.0 in lineare

METALLI:
  Base Color (F0):    180–255 sRGB per la maggior parte
  Sotto 140 sRGB con Metallic=1: ERROR fisico
  Colore atteso per tipo:
    Oro:   R >> G > B (~255, 220, 100)
    Rame:  R >> B (~250, 208, 192)
    Ferro: grigio neutro (~196, 199, 199)
    Alluminio: freddo, B leggermente > R (~245, 246, 246)

SPECULAR F0 UNIVERSALE:
  Dielettrici comuni: 0.04 (4%) = IOR ~1.5
  Eccezione validata: Legno grezzo → 0.04-0.05
  Range gemme: 0.05-0.17
  Metalli: sempre > 0.50

ROUGHNESS per categoria:
  Specchio ottico, vetro lucido: 0.00-0.05
  Metallo lucidato, ceramica: 0.05-0.15
  Legno verniciato, plastica semi-lucida: 0.10-0.30
  Legno grezzo, mattone: 0.60-0.85
  Cemento, pietra non levigata: 0.70-0.95
  Tessuto, terra: 0.75-1.00
```

### 3.4 Physics Oracle — Aggiornamento Continuo

Il database cresce con la ricerca. Ogni aggiornamento segue questo protocollo:
1. Nuova fonte identificata (articolo, dataset, video)
2. Dati estratti e validati manualmente
3. Aggiunti nel file appropriato con `source` e `date_added`
4. I nuovi profili vengono automaticamente disponibili al Validator al prossimo run

---

## 4. PIPELINE COMPLETA — MODULI IN SEQUENZA

### MODULO 1 — Ingestor *(invariato da v2)*
### MODULO 2 — Naming Intelligence (NID) *(invariato da v2)*
### MODULO 3 — Metadata Extractor *(invariato da v2)*
### MODULO 4 — Normalizer *(invariato da v2)*

---

### MODULO 5 — Physics Validator (AGGIORNATO)
**Layer:** Deterministic Core + Physics Oracle
**Input:** file normalizzati + Physics Oracle
**Output:** `physics_validation.json` per ogni file + per il materiale nel suo insieme

Esteso rispetto alla v2 con validazione fisica profonda:

**5a. Standard PBR Checks** (da v2, invariati):
histogram albedo, metallic binarity, vector normalization, color space, resolution consistency

**5b. Physics-Grounded Checks** (nuovo):
Confronto contro profili Physics Oracle per il material type rilevato dal Naming/AI.

Se il materiale è identificato come "Copper":
```
CHECK: albedo_R > albedo_B             → atteso true per rame
CHECK: metallic == 1.0 ± 0.05         → atteso true per metallo puro
CHECK: albedo_mean_luminance in [0.60, 0.72] → range fisico rame
CHECK: roughness_mean in [0.30, 0.60]  → range standard rame non-ossidato
```

**5c. Seamless Score, Convention Detection, pHash** *(da v2, invariati)*

**5d. Scale Estimation** (nuovo):
Stima la scala fisica reale che la texture rappresenta basandosi su:
- Dimensione dei pattern rilevati (ampiezza fuga mattoni = ~10-15mm → tile 215×65mm → sezione 2-4 file)
- Database delle dimensioni fisiche reali degli elementi architettonici
- Confronto con texel density standard (1024 px/m = standard produzione)

```json
{
  "scale_estimation": {
    "method": "pattern_recognition + physics_oracle",
    "estimated_real_world_coverage": "0.88m × 0.60m",
    "element_identified": "standard_brick_wall_4courses",
    "texel_density_at_4K": "4654 px/m",
    "texel_density_normalized": "1024 px/m at 878px equivalent",
    "confidence": 0.82,
    "notes": "Based on standard brick 215×65mm, 3mm mortar joint"
  }
}
```

**5e. Normal Convention Detection** *(da v2, invariato)*

**5f. Tiling Quality Analysis** (esteso da v2):
FFT 2D + analisi bordi + rilevamento seam. Output:
```json
{
  "tiling_analysis": {
    "seamless_score": 0.91,
    "seam_locations": ["right_edge", "none_top_bottom"],
    "seam_severity": "subtle",
    "repeating_pattern_detected": true,
    "pattern_scale_px": [256, 256],
    "tiling_improvement_suggested": "fix_right_seam_dilation"
  }
}
```

---

### MODULO 5b — Cross-Map Correlation Analyzer (NUOVO)
**Layer:** Deterministic Core
**Input:** tutti i file del set normalizzati
**Output:** `cross_map_correlations.json`

Questo modulo studia le **correlazioni fisiche attese tra le mappe** e segnala dove mancano o sono incoerenti. È la base per il Coherent Edit Propagator del Layer 3.

**Correlazioni fisiche attese:**

```
Normal ↔ Height:
  La Normal map è il gradiente della Height map.
  Ogni variazione significativa di altezza genera variazione normale.
  CORRELAZIONE ATTESA: alta (r > 0.7)
  SE BASSA: Normal o Height generata in modo incoerente

Roughness ↔ AO:
  Zone ad alta occlusione (cavità, fessure) tendono ad avere roughness più alta
  per accumulo di micro-detriti fisici.
  CORRELAZIONE ATTESA: moderata-alta (r > 0.5)
  SE INVERSA: possibile errore di spazio colore su uno dei due

Metallic ↔ Base Color:
  Se Metallic = 1 in una zona, Base Color deve contenere F0 alto (180+ sRGB).
  Se Metallic = 0, Base Color deve contenere albedo diffusa.
  CROSS-CHECK: identifica pixel dove Metallic=1 e Base Color < 100 sRGB → fisica impossibile

Curvature/Edges ↔ Roughness:
  Bordi convessi esposti tendono ad essere più levigati (usura) o più ruvidi (danno).
  Concavità tendono ad accumulare sporco (roughness alta).
  Derivato dalla Normal map tramite curvature extraction.

Damage/Scratches in BaseColor ↔ Normal:
  Se c'è un graffio visibile nel BaseColor (banda scura), deve esistere variazione
  corrispondente nella Normal (il graffio ha profondità fisica).
  DETECTION: usa edge detection su BaseColor, verifica correlazione con Normal grad
```

**Output per coppia:**
```json
{
  "pair": ["normal", "height"],
  "correlation_coefficient": 0.83,
  "status": "coherent",
  "anomalies": []
},
{
  "pair": ["basecolor_edges", "normal_corresponding"],
  "correlation_coefficient": 0.31,
  "status": "potentially_incoherent",
  "anomalies": [
    {
      "type": "scratch_in_color_no_normal",
      "location_approx": "center-right, 30% from top",
      "severity": "moderate",
      "suggested_action": "propagate_to_normal"
    }
  ]
}
```

---

### MODULO 6 — Decision Layer (AGGIORNATO)
**Layer:** Decision Engine
**Input:** output Physics Validator + Cross-Map Analyzer
**Output:** `decisions.json` — lista azioni con priorità e modalità

Esteso con nuove decisioni fisicamente motivate:

```json
{
  "material_id": "DVA_QXL_BrickWall01",
  "decisions": [
    {
      "trigger": "scratch_in_color_no_normal_correlation",
      "source_module": "cross_map_correlation",
      "action": "propagate_damage_to_normal",
      "parameters": {
        "damage_type": "scratch",
        "depth_estimate": 0.3,
        "roughness_change": "+0.15 in affected zone"
      },
      "priority": "high",
      "auto_apply": false,
      "physics_basis": "Mechanical damage creates surface depression (Normal) and increases micro-roughness"
    },
    {
      "trigger": "mortar_joint_normal_too_flat",
      "source_module": "physics_validator",
      "action": "enhance_mortar_normal_detail",
      "parameters": {
        "zone": "pid_zone_2_mortar",
        "expected_profile": "cement_mortar",
        "target_roughness": [0.80, 0.95],
        "micro_detail": "porous_cavity"
      },
      "priority": "medium",
      "auto_apply": false,
      "physics_basis": "Cement mortar has pronounced cavity structure and high surface porosity"
    },
    {
      "trigger": "tiling_seam_detected_right_edge",
      "source_module": "tiling_analyzer",
      "action": "apply_seam_fix_dilation",
      "priority": "high",
      "auto_apply": true
    },
    {
      "trigger": "roughness_too_uniform_for_material",
      "source_module": "physics_validator",
      "action": "increase_roughness_variation",
      "parameters": {
        "target_std_dev": 0.12,
        "material_reference": "stone_granite"
      },
      "priority": "low",
      "auto_apply": false
    }
  ]
}
```

---

### MODULO 7 — AI Semantic Analyzer *(aggiornato)*
**Layer:** Semantic AI
Identico alla v2 per classificazione e damage detection.

**Aggiunta — Material Physics Contextualization:**
Dopo la classificazione LLaVA, il risultato viene confrontato con il Physics Oracle per il material type rilevato. Se LLaVA classifica "Granite", vengono caricati i range fisici del granito come contesto per le analisi successive. Questo aumenta la precisione delle decisioni del Layer 3.

---

### MODULO 8 — SAM P-ID Generator *(aggiornato)*
**Layer:** Semantic AI
Il processo a tre passi della v2 è invariato. Aggiunta:

**Pass 4 — Physics Profile Assignment:**
Per ogni zona rilevata da SAM e classificata da LLaVA, viene assegnato il profilo fisico corrispondente dal Physics Oracle.

Una zona classificata come "Mortar Joint" riceve automaticamente:
```json
{
  "zone_physics_profile": {
    "material": "cement_mortar",
    "albedo_srgb_range": [160, 200],
    "roughness_range": [0.80, 0.95],
    "specular_f0": 0.04,
    "micro_detail": "porous",
    "source": "physics_oracle_cement_mortar"
  }
}
```

Questo profilo viene usato dalla Coherent Edit Propagation per calibrare le correzioni zona per zona.

---

### MODULO 8b — Cross-Material Comparator (NUOVO)
**Layer:** Semantic AI
**Input:** due o più material set dello stesso dataset
**Output:** `cross_material_analysis.json`

Compara materiali diversi per estrarre pattern di comportamento delle mappe per tipo fisico.

**Usi:**
- Capire come la Normal map si comporta su stone vs concrete vs wood
- Identificare il "fingerprint" di roughness per ogni categoria
- Costruire benchmark statistici per ogni tipo di mappa × tipo materiale
- Identificare anomalie per confronto (questo mattone ha roughness troppo bassa rispetto agli altri mattoni nel dataset)

**Schema output:**
```json
{
  "comparison_group": "brick_materials",
  "materials_compared": ["DVA_QXL_BrickWall01", "DVA_AMB_OldBrick02", "DVA_POL_MedBrick01"],
  "normal_map_analysis": {
    "frequency_profile": "medium-high across all",
    "common_features": ["mortar_cavity", "surface_texture"],
    "outlier": "DVA_POL_MedBrick01 has unusually smooth normals for brick"
  },
  "roughness_statistics": {
    "mean_range": [0.72, 0.88],
    "std_dev_range": [0.08, 0.15],
    "outlier_detection": "DVA_QXL_BrickWall01: roughness_mean 0.91 is above expected range"
  }
}
```

---

### MODULO 9 — Map Generator (AGGIORNATO)
**Layer:** Deterministic Core
Identico alla v2 per la generazione standard. Aggiunto:

**9a. Physics-Calibrated Generation:**
Le mappe generate usano il profilo fisico del Physics Oracle come vincolo.
Se genero Roughness per un mattone, il range target è 0.72–0.88 (non un generico 0–1).

**9b. Coherent Damage Propagation** (da Decision Layer):
Se il Decision Layer ha identificato un graffio nel BaseColor senza corrispondenza in Normal:
1. Estrae la maschera della zona del graffio dal BaseColor (edge detection + thresholding)
2. Genera la deformazione normale corrispondente (gaussian bump map scalata per profondità stimata)
3. Aumenta roughness nella zona del graffio (+0.15 stimato)
4. Riduce leggermente AO ai bordi del graffio (il bordo è esposto)
Tutti i file generati sono `class: "derived"`, con riferimento alla decisione che li ha creati.

**9c. Materialize / Substance / Photoshop Integration:**
I file prodotti da workflow esterni (Materialize, Substance Designer, Photoshop) entrano nel sistema come `class: "derived"` con `source: "materialize | substance_designer | photoshop"`. Vengono processati dal Comparator come qualsiasi altra mappa derivata.

---

### MODULO 9b — Variant Generator (NUOVO)
**Layer:** Semantic AI + Deterministic Core
**Input:** materiale completamente processato + Decision Layer
**Output:** varianti in `02_PROCESSING/synthetic/variants/`

Genera varianti fisicamente plausibili del materiale di base. Non usa AI generativa — usa trasformazioni deterministiche guidate dal Physics Oracle.

**Varianti supportate:**

**Broken Tile Variant:**
- Seleziona N tile nella griglia (da Scale Estimation)
- Applica pattern di rottura realistico (crack pattern library, geometrie di frattura tipiche)
- Propaga rottura su tutte le mappe: BaseColor (esposizione materiale interno), Normal (geometria rottura), Height (depressione), Roughness (zona frattura più ruvida), AO (ombra nella frattura)
- `class: "derived"`, `source: "deterministic_variant_broken"`

**Wet Variant:**
- Applica i 4 step del Wetness System (da DVAMOCLES Core 3.1 §9.6):
  1. BaseColor × 0.7–0.85 (assorbimento acqua)
  2. Roughness → 0.05–0.15 (film acqua)
  3. Specular sopra 0.04 (IOR acqua ~1.333)
  4. AO × pooling factor (accumulo cavità)
- `class: "derived"`, `source: "deterministic_variant_wet"`

**Dirty Variant:**
- Applica layer sporco basato sul profilo fisico (dove si accumula sporco per quel materiale)
- AO alto = accumulo sporco → scurisce BaseColor, aumenta Roughness
- Usa physics_oracle cross_material_patterns per il tipo di sporco atteso
- `class: "derived"`, `source: "deterministic_variant_dirty"`

**Aged Variant:**
- Combina usura bordi (curvatura positiva → rimozione layer superficiale), sporco cavità, degradazione roughness
- `class: "derived"`, `source: "deterministic_variant_aged"`

---

### MODULO 10 — Comparator *(aggiornato)*
**Layer:** Deterministic Core
Identico alla v2 per SSIM/PSNR/histogram/FFT. Aggiunto:

**10a. Physics Compliance Score:**
Confronta ogni mappa contro il profilo Physics Oracle del material type. Output: `physics_compliance: 0.0–1.0` che misura quanto il materiale si comporta come deve fisicamente.

---

### MODULO 11 — Asset Parser *(invariato da v2)*

---

### MODULO 12 — Dataset Builder *(aggiornato)*
**Layer:** Decision Engine
Assembla i tre livelli di output:
- **MASTER JSON** (Tier 2 Runtime) — identico a v2
- **RAW JSON** (Tier 1 Dataset) — esteso con sezioni Physics Oracle e cross-map
- **SQLite Index** — esteso con colonne physics compliance e scale estimation

---

## 5. SCHEMA JSON v3 — AGGIORNAMENTI CHIAVE

### 5.1 Nuove sezioni nel RAW JSON

```json
{
  "_extends": "[MatName]_master.json",
  "tier": "dataset",

  "physics_validation": {
    "physics_oracle_profile_used": "brick_standard",
    "physics_compliance_score": 0.87,
    "checks": [
      {
        "check_id": "albedo_range_brick",
        "status": "pass",
        "detected": 148,
        "expected_range": [120, 160],
        "severity": "info"
      },
      {
        "check_id": "mortar_roughness",
        "status": "warning",
        "detected": 0.71,
        "expected_range": [0.80, 0.95],
        "severity": "warning",
        "decision_triggered": "enhance_mortar_normal_detail"
      }
    ]
  },

  "cross_map_correlations": {
    "normal_height": {
      "correlation": 0.83,
      "status": "coherent"
    },
    "roughness_ao": {
      "correlation": 0.61,
      "status": "coherent"
    },
    "basecolor_damage_normal": {
      "correlation": 0.31,
      "status": "potentially_incoherent",
      "anomalies": [
        {
          "type": "scratch_in_color_no_normal",
          "location": "center-right",
          "severity": "moderate"
        }
      ]
    }
  },

  "scale_estimation": {
    "estimated_coverage": "0.88m × 0.60m",
    "element_identified": "standard_brick_wall_4courses",
    "texel_density_at_4K": "4654 px/m",
    "confidence": 0.82
  },

  "tiling_analysis": {
    "seamless_score": 0.91,
    "seam_locations": ["right_edge"],
    "seam_severity": "subtle",
    "improvement_suggested": "apply_seam_fix_dilation"
  },

  "cross_material_comparison": {
    "comparison_group": "brick_materials",
    "roughness_rank_in_group": 2,
    "outlier_flags": [],
    "physics_compliance_vs_group": 0.89
  },

  "variants_generated": [
    {
      "variant_type": "wet",
      "path": "variants/[MatName]_wet_4K.png",
      "class": "derived",
      "source": "deterministic_variant_wet"
    },
    {
      "variant_type": "broken_tile",
      "path": "variants/[MatName]_broken_4K.png",
      "class": "derived",
      "source": "deterministic_variant_broken"
    }
  ],

  "multi_material_blending": null
}
```

---

## 6. MODULO MULTI-MATERIAL BLENDING ADVISOR (NUOVO)

### 6.1 Scopo

Quando un set di texture comprende due materiali fisici distinti (es. terra + pietra, erba + terra) o quando l'utente importa due set da blend tra loro, il sistema analizza come integrarli fisicamente in modo corretto.

### 6.2 Analisi di Integrazione

Il sistema studia:

**Boundary Analysis:**
Come si comporta il confine tra i due materiali. Una pietra che emerge da terra ha:
- Bordo ombrato sul lato interrato (AO alto)
- Normale di transizione sfumata (non taglio netto)
- Roughness che aumenta gradualmente dalla pietra levigata alla terra

**IOR Compatibility:**
Confronta gli IOR dei due materiali. Un grande divario IOR (es. metallo 0.18 vs dielettrico 1.5) richiede gestione speciale al confine — possibile color bleeding fisicamente giustificato.

**Blending Map Recommendation:**
Basato sui profili Physics Oracle dei due materiali, suggerisce come costruire la blend mask:
- Height-based blend (pietra sopra, terra nelle depressioni)
- Normal-based blend (pietra dove la normale è più verticale)
- AO-based blend (terra nelle zone occluse)

**Output:**
```json
{
  "material_a": "DVA_QXL_Stone01",
  "material_b": "DVA_AMB_Dirt01",
  "blend_analysis": {
    "recommended_blend_driver": "height_map",
    "ior_compatibility": "normal",
    "boundary_behavior": "gradual_transition",
    "transition_zone_width": "5-15 cm real world",
    "suggestions": [
      "Use Height blend: stone emerges from dirt in high points",
      "Add AO darkening in transition zone (dirt accumulates in edges)",
      "Stone roughness should increase slightly near dirt boundary (contamination)"
    ]
  }
}
```

---

## 7. APPENDICE C — DATI SINTETICI *(invariata da v2)*

---

## 8. APPENDICE D — PHYSICAL PROCESS CAPTURE *(invariata da v2)*

---

## 9. APPENDICE E — INTEGRAZIONE FLUSSI ESTERNI

### E.1 Materialize

Le mappe prodotte da Materialize entrano nel sistema come `class: "derived"`, `source: "materialize"`. Il Comparator le confronta automaticamente con le mappe originali (se esistono) o con i profili Physics Oracle (se sono le uniche disponibili).

Workflow operativo:
1. Ingestor rileva file in `02_PROCESSING/[MatName]/generated/`
2. Naming Intelligence li associa al materiale padre e al tipo mappa
3. Comparator esegue confronto vs originale se presente
4. Physics Validator verifica compliance con Physics Oracle
5. Cross-Map Analyzer li include nelle correlazioni del set completo

### E.2 Photoshop / Substance Designer

Stessa pipeline di Materialize. Il campo `source` viene compilato dal naming del file o dall'utente durante la review. Mappe prodotte in Photoshop spesso richiedono verifica dello spazio colore — il Metadata Extractor e il Validator lo segnalano automaticamente.

### E.3 File custom utente (mappe extra)

Qualsiasi file importato dall'utente che non segue i pattern NID standard viene flaggato per review manuale in The Analyzer. L'utente assegna il tipo mappa, e il sistema prosegue la pipeline normalmente.

---

## 10. SENTINEL — COSA DIVENTA IL DATASET

Ogni materiale processato dalla pipeline produce per Sentinel:

**Training data per NID:**
- Filename + tipo mappa assegnato + confidence → affina le regex del Naming Intelligence Database
- Pattern provider specifici accumulati nel tempo

**Training data per Material Health Check:**
- Violazioni rilevate + material type + valore → il sistema impara i range normali per tipo
- Cross-map correlations → il sistema impara cosa è coerente e cosa non lo è

**Training data per P-ID Mask:**
- Immagini segmentate + zone etichettate → migliora la qualità della segmentazione automatica
- Profili fisici per zona → migliora l'assegnazione automatica dei profili materiale

**Training data per Map Generation:**
- Coppie (mappa mancante derivata, originale) → il sistema impara a generare mappe plausibili
- Physics compliance scores → il sistema impara i vincoli fisici di ogni tipo di mappa

**Training data per Coherent Editing:**
- Decisioni applicate + result → il sistema impara come propagare modifiche in modo fisicamente corretto
- Varianti generate + physics scores → benchmark per la qualità delle varianti

---

## 11. WORKFLOW OPERATIVO (HUMAN-IN-THE-LOOP)

### 11.1 Sessione Singolo Materiale (modalità guidata)

**Step 1 — Ingest + Naming (automatico):**
Inserisci la cartella del materiale. Il sistema produce l'inventory manifest e le assegnazioni NID.
Revisione: controlla le assegnazioni con confidence < 0.80.

**Step 2 — Physics Validation (automatico + review):**
Il sistema confronta il materiale con i profili Physics Oracle. Mostra i check failed e le decisioni suggerite.
Revisione: approva/rifiuta le decisioni con `auto_apply: false`.

**Step 3 — Cross-Map Analysis (automatico):**
Il sistema rileva le correlazioni tra mappe e le anomalie.
Revisione: decide se propagare le correzioni suggerite.

**Step 4 — PID + AI Enrichment (semi-automatico):**
SAM + LLaVA producono mask e label. L'utente verifica le zone e le etichette.

**Step 5 — Variant Generation (opzionale, automatico):**
Seleziona quali varianti generare. Il sistema le produce.

**Step 6 — Export (automatico):**
Dataset Builder produce Master JSON + RAW JSON + aggiorna SQLite.

### 11.2 Ordine di Implementazione

**Fase 1 — Core:** Moduli 1, 2, 3, 4, 6, 12 + Physics Oracle stub
**Fase 2 — Physics:** Modulo 5 completo + Cross-Map Analyzer (5b) + Scale Estimator
**Fase 3 — AI:** Moduli 7, 8 + Cross-Material Comparator (8b)
**Fase 4 — Generation:** Moduli 9 (physics-calibrated) + 9b (variants) + Blending Advisor
**Fase 5 — Appendici:** C (synthetic) + D (PPC) + E (external flows)

---

## 12. STACK TECNOLOGICO (aggiornato)

| Componente | Tool | Uso |
|---|---|---|
| Linguaggio | Python 3.11+ | runtime unico |
| Metadata | ExifTool + PyExifTool | EXIF/XMP extraction |
| Image I/O | Pillow + OpenCV | tutti i formati |
| FFT + stats | NumPy + SciPy | frequenze, correlazioni |
| Perceptual Hash | ImageHash | deduplicazione |
| SSIM/PSNR | scikit-image | comparazione qualità |
| Correlazione maps | SciPy + NumPy | cross-map analysis |
| Segmentazione | Meta SAM 2 | P-ID Mask |
| AI Vision | Ollama + LLaVA 13B | semantica locale |
| Physics Oracle | JSON + SQLite | reference fisico |
| Pattern library | JSON custom | crack/damage patterns |
| Scale estimation | OpenCV feature + DB | riconoscimento elementi |
| Asset Parsing | bpy + UModel | .blend / .uasset |
| Database Index | SQLite | query veloci |
| Config | PyYAML | pipeline config |

---

*Documento: DVAMOCLES SWORD™ — SIGNUM SENTINEL Dataset & Intelligence Protocol v3.0*
*Generato: 2026-04-20 | Sostituisce v2.0*
*Fonti: Dataset Protocol v1.0/v2.0 + PBR_MKB_A/B/C + Physically Based Database + IOR Data + GPT/Gemini analyses*
*Prossimo step: Prompt 2 — Core Backend Python (Fase 1: Moduli 1–6 + 12 + Physics Oracle stub)*
