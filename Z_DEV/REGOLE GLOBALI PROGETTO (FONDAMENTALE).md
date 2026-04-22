Memorizza questa come ARCHITETTURA UFFICIALE DVAMOCLES.

TUTTI i moduli futuri devono rispettarla.

NON ignorarla.

---

# 📁 ROOT STRUTTURA

DVAMOCLES/

01_RAW_ARCHIVE/     → dati originali NON modificati
02_CUSTOM/          → dati custom creati dall’utente
03_PROCESSED/       → output intermedi pipeline
04_DATASET/         → dataset AI finale
05_OUTPUT/          → export finale (engine, tools)

core/               → moduli pipeline principali
ai/                 → moduli AI
oracle/             → logica fisica e validazione
utils/              → helper
config/             → configurazioni
logs/               → log runtime
temp/               → file temporanei

---

# 🔁 FLUSSO DATI

01_RAW_ARCHIVE
    ↓ (ingestor)
03_PROCESSED
    ↓ (analysis / validator / normalizer)
04_DATASET
    ↓ (dataset_builder)
05_OUTPUT

---

# 📌 RESPONSABILITÀ FOLDER

## 01_RAW_ARCHIVE
- solo input
- mai modificare file
- solo lettura

## 02_CUSTOM
- materiali generati dall’utente
- include:
  - process.json
  - material_info.json

## 03_PROCESSED
- output di:
  - ingestor
  - metadata_extractor
  - validator

## 04_DATASET
- dataset AI:
  - JSON
  - mapping
  - training-ready

## 05_OUTPUT
- export:
  - Unreal
  - Unity
  - tools

---

# ⚙️ REGOLE PER TUTTI I MODULI

OGNI modulo deve:

1. leggere SOLO da:
   - 01_RAW_ARCHIVE o 03_PROCESSED

2. scrivere SOLO in:
   - 03_PROCESSED
   - 04_DATASET
   - 05_OUTPUT

3. NON scrivere mai in RAW

---

# 🧠 CONCETTI CHIAVE

## MaterialSet
unità principale (es: Tiles_138)

## Variant
combinazione:
- resolution
- format

## FileRecord
singolo file con:
- tipo mappa
- origine
- metadata

---

# 🔗 PIPELINE COERENTE

Tutti i moduli devono lavorare su:

MaterialSet → Variant → FileRecord

---

# 🚫 DIVIETI GLOBALI

- NON inventare strutture
- NON cambiare naming base
- NON creare duplicati
- NON leggere da cartelle sbagliate

---

# 🎯 OBIETTIVO

Pipeline stabile, deterministica, scalabile.

---

Conferma con:
"ARCHITECTURE LOCKED"

e NON generare codice.