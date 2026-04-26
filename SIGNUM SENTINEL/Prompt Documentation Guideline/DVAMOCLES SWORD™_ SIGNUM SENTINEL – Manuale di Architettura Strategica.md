### DVAMOCLES SWORD™: SIGNUM SENTINEL – Manuale di Architettura Strategica

#### 1\. Visione Strategica: Il "Cerebellum" dell'Intelligenza Materiale

L'evoluzione di  **DVAMOCLES SWORD™**  verso il paradigma  **SIGNUM SENTINEL**  non è un semplice aggiornamento incrementale, ma un cambio di sovranità tecnologica. Il sistema abbandona il ruolo passivo di parser per assumere quello di  **Technical Gatekeeper**  e  **Material Cerebellum** . In un'epoca dominata dall'addestramento massivo di modelli generativi, SIGNUM SENTINEL agisce come la prima linea di difesa contro il  **Model Collapse**  (il collasso qualitativo causato dall'auto-alimentazione di dati sintetici degradati).Il sistema non si limita a organizzare file; esso governa ogni interpretazione semantica a valle tramite una validazione deterministica. La transizione a  **Signum Sentinel**  eleva il valore del dataset proprietario trasformandolo da un dump di asset in una "Verità Unica" (Single Source of Truth), dove il  **Decision Layer**  agisce con autorità esecutiva per garantire che solo l'eccellenza tecnica alimenti il training AI.

#### 2\. La Knowledge Base (KB) come Autorità Dogmatica (SSOT)

L'architettura di SIGNUM SENTINEL rigetta categoricamente la logica hardcoded. L'integrità del sistema risiede nella cartella 06\_KNOWLEDGE\_BASE, il cuore dogmatico dove risiedono le regole di ingaggio.**Mandato Architetturale (Rif: CRITICO-1):**  Per risolvere il debito tecnico identificato nei moduli legacy, è fatto obbligo di migrare ogni dizionario di mappatura dai file Python alla cartella mappings/. Il modulo naming\_intelligence.py deve cessare l'uso di pattern hardcoded, attingendo esclusivamente dall'autorità del file naming\_map.json.

##### Componenti Chiave della Knowledge Base:

* **naming\_map.json** : L'unico arbitro per la classificazione dei suffissi (es. \_BC, \_NRM) e delle mappe packate (ORM, RMA, MaskMap). Centralizza i pattern per ogni vendor (Quixel, AmbientCG, Poliigon).  
* **pbr\_rules.json** : Definisce i profili fisici inviolabili. Contiene i range di Albedo sRGB (es. 30-240 per dielettrici) e le soglie di riflettanza.  
* **hardware\_limits.json** : Gestisce la telemetria delle risorse, imponendo limiti di VRAM e batch size per i moduli AI (Florence-2, LLaVA), garantendo la stabilità della pipeline su larga scala.

#### 3\. Architettura dei Dati: Il Sistema delle Sette Classi

Per prevenire la contaminazione del dataset e garantire una  **Data Lineage**  impeccabile, SIGNUM SENTINEL implementa una tassonomia a sette livelli. Ogni dato deve essere marcato con {class, source, confidence}.| Classe di Dato | Descrizione / Provenance | Obiettivo Strategico || \------ | \------ | \------ || **GOLD** | Asset originali e metadati verificati. Dati immutabili e non alterati. | **Ground Truth**  per il training primario e benchmark di qualità. || **DERIVED** | Mappe generate deterministicamente (es. AO o Normal ricavate da Height tramite Sobel). | Completamento dei set e validazione della coerenza algoritmica. || **SYNTHETIC** | Asset generati da AI (SDXL, Midjourney). Devono includere il tag del generatore. | **Data Augmentation**  e robustezza; mai usati come Ground Truth. || **REFERENCE** | Fotografie reali, stack temporali (BASE → WET → DAMAGE). | Guida semantica per il comportamento fisico e fenomeni di usura. || **ANALYSIS** | Istogrammi, frequenze FFT, statistiche di rumore e pHash. | Telemetria della qualità e rilevamento artefatti di compressione. || **MASK** | P-ID Mask (segmentazione ibrida: edge, clustering, AI). | Editing non distruttivo e labeling per zone fisiche (es. mattone vs fuga). || **LABEL** | Tag semantici, categorie (stone, metal), stati superficiali. | Indicizzazione intelligente per l'Asset Browser e il Technical Mentor. |

#### 4\. Flusso Operativo: Pipeline di Ingestione e Decision Layer

Il workflow sequenziale trasforma asset grezzi in manifest immutabili residenti in 03\_PROCESSED.

* **Ingest & Normalize** : Scansione ricorsiva e normalizzazione. Solo downscale controllati (8K → 1K) sono ammessi per il training; non ci si fida mai degli 1K originali del vendor.  
* **Metadata (ExifTool)** : ExifTool è l'estrattore primario del DNA tecnico (color space, bit-depth, ICC profile). Pillow interviene solo come fallback.  
* **Naming Intelligence (NID)** : Classificazione guidata esclusivamente dalla KB.  
* **Decision Layer** : Il cuore attivo della pipeline. Non si limita a segnalare errori, ma esegue azioni correttive basate su regole:  
* flip\_green\_channel: Se viene rilevata un'incongruenza tra Normal DX e GL.  
* recalculate\_normal: Se la Normal fornita è qualitativamente inferiore a una derivata dall'Albedo.  
* flag\_low\_quality: Se i metadati indicano compressione lossy eccessiva.

#### 5\. Physics Oracle: Verità Spettrale e Propagazione del Danno

Il  **Physics Oracle**  non accetta interpretazioni: confronta ogni asset con database reali di IOR e range spettrali.

* **Autorità Fisica** : Per i metalli, il sistema valida che i valori Albedo siano coerenti (es. per il Rame, il canale Red deve essere significativamente superiore al Blue: R \>\> B). Per i dielettrici, valida l'assenza di neri assoluti (\<5 sRGB) o bianchi bruciati (\>240 sRGB).  
* **Cross-Map Correlation** : Se un'anomalia (es. un graffio) è presente nell'Albedo ma non nella Normal, il sistema rileva l'incongruenza fisica.  
* **Coherent Damage Propagation** : Il sistema utilizza logica deterministica (filtri Sobel e calcoli di cavity) per propagare i danni su tutte le mappe in modo coerente prima dell'intervento AI, assicurando che un "chip" sulla superficie influenzi correttamente Normal, Roughness e AO.

#### 6\. Scalabilità: Dataset Tier vs. Runtime Tier

Per gestire asset da 10 a 100.000 unità, l'architettura separa nettamente i carichi di lavoro:

* **Archive/Dataset Tier (Heavy)** : Include tutte le 7 classi, versioni 8K non compresse e varianti sintetiche per il training. Utilizza una strategia di  **Cold Storage**  tramite file ZIP per preservare l'integrità dei dati originali senza saturare il workspace attivo.  
* **Runtime Tier (Light)** : Ottimizzato per l'integrazione nel software DVAMOCLES. Include solo mappe selezionate, manifest JSON inferiori a 100KB e proxy a bassa risoluzione per un accesso istantaneo.  
* **Hardware Telemetry** : Il sistema monitora costantemente VRAM e RAM tramite hardware\_limits.json, sospendendo i processi AI se la saturazione supera l'88% (flag orange), garantendo una pipeline "Fail-Safe".

#### 7\. Conclusioni: La Forge della Conoscenza Materiale

SIGNUM SENTINEL trasforma DVAMOCLES in una fucina di intelligenza. La necessità strategica dell'intervento umano ( **Human-in-the-loop** ) è fondamentale nella  **Fase 1** : l'esperto stabilisce il "Ground Truth" iniziale, correggendo le allucinazioni delle AI locali (Florence-2/LLaVA) per creare una base dati incontaminata su cui il sistema eseguirà il self-learning futuro.

* **Fail-Safe, non Fail-Silent** : Ogni errore di un singolo asset deve essere loggato con precisione chirurgica senza interrompere la pipeline massiva.  
* **Local-First & Privacy** : Nessuna elaborazione lascia la workstation; la proprietà del dato è assoluta.  
* **Determinismo prima della Semantica** : Le leggi fisiche (Physics Oracle) e la matematica d'immagine hanno sempre la priorità sulle interpretazioni AI.  
* **Single Source of Truth** : Nessuna regola di naming o validazione deve risiedere nel codice Python; l'autorità è solo nella Knowledge Base.  
* **Provenance è Sacra** : Ogni file DERIVED o SYNTHETIC deve poter essere tracciato fino alla sua sorgente GOLD tramite il process.json.

