### Protocollo Operativo di Integrità: Classificazione e Provenienza Asset PBR

#### 1\. Introduzione e Missione del Protocollo

Il presente documento è il  **Single Source of Truth**  (SSOT) per l'integrità dei dati all'interno dell'ecosistema  **DVAMOCLES SWORD** . In qualità di Direttore della Qualità AI, stabilisco che la purezza del dato di addestramento è l'unico asset strategico non negoziabile per lo sviluppo di sistemi di Intelligenza Artificiale orientati al Physically Based Rendering (PBR). Un dataset corrotto da metadati errati o da una fisica incoerente non è solo inutile, è dannoso per la convergenza dei modelli neurale di SIGNUM SENTINEL.L'integrità del progetto riposa su tre pilastri architettonici fondamentali:**I Principi Fondamentali dell'Integrità**

* **La Provenienza è Sacra:**  Ogni singolo bit deve essere tracciabile fino alla sua origine GOLD. Un dato privo di lineage è considerato "tossico" e verrà immediatamente rimosso dalla pipeline per prevenire la corruzione del sistema.  
* **Non-Distruttività:**  La directory 01\_RAW\_ARCHIVE è un vault inviolabile. Qualsiasi trasformazione deve avvenire in layer isolati, garantendo che la "Ground Truth" rimanga incorrotta.  
* **Deterministico:**  Ogni operazione di analisi o generazione (Layer 0 e Layer 1\) deve produrre risultati identici e verificabili. La discrezionalità è bandita dalla pipeline core.La qualità dell'intero apparato dipende dalla separazione chirurgica delle classi di dati e dalla rigorosa osservanza dei criteri di tracciabilità qui definiti.

#### 2\. Architettura della Classificazione Dati (Tier System)

Per prevenire il "caos dei dati" durante i processi di batch processing, è fatto obbligo di categorizzare ogni asset secondo la tassonomia a sette classi derivata dalla Specifica 3.0. Questo sistema garantisce che il  **Decision Layer**  possa distinguere tra verità fisica e ipotesi sintetica.

##### Tassonomia delle Classi Asset (Data Tiering)

Classe,Descrizione,Utilizzo  
GOLD,"Dati originali, affidabili e non alterati (Ground Truth).",Validazione e addestramento primario.  
DERIVED,Mappe generate tramite algoritmi deterministici (es. AO da Height).,Completamento set PBR e data augmentation.  
SYNTHETIC,Asset generati integralmente da IA (es. Stable Diffusion).,Test di robustezza e diversificazione stilistica.  
REFERENCE,"Foto reali, riferimenti visivi o scansioni non calibrate PBR.",Guida semantica e studio del comportamento fisico.  
ANALYSIS,"Feature estratte quantitativamente (istogrammi, FFT tiling score).",Metadati analitici per il Decision Layer.  
MASK,Segmentazioni fisiche e P-ID Masks (Hybrid SAM 2).,Layer di zonizzazione fisica del materiale.  
LABEL,Tag semantici e metadati di classificazione materiale.,Layer di comprensione semantica dell'IA.

##### Separazione tra Dataset e Runtime

Il sistema deve operare su due livelli fisicamente distinti:

1. **Tier 1: Archive (Heavy Dataset):**  Risiede offline o in storage ad alta capacità. Contiene tutte le risoluzioni (da 1K a 8K), le varianti SYNTHETIC e i file REFERENCE. È il cuore dell'addestramento.  
2. **Tier 2: Workspace (Light Runtime):**  Un manifest leggero (\<100KB) utilizzato dal software in esecuzione. Contiene solo i link agli asset ottimizzati e i parametri fisici necessari per le operazioni real-time.

##### Segmentazione P-ID Hybrid

Le maschere P-ID (Physical ID) devono essere generate tramite un approccio  **Ibrido** . È vietata la segmentazione puramente basata su AI. Il sistema deve combinare:

* Deterministic Clustering (matematica dei bordi su Normal e Height).  
* AI Segmentation (tramite  **SAM 2** ) per la rifinitura semantica.  
* L'obiettivo è isolare zone fisiche distinte (es. Mattoni vs Malta) per validazioni fisiche per-zone.

#### 3\. Gestione della Provenienza: Il Mandato process.json

L'integrità del lineage è garantita dall'obbligatorietà del file process.json per ogni materiale nella directory 02\_CUSTOM. Senza questo certificato, l'asset è considerato orfano e privo di valore scientifico.**Anatomia obbligatoria del Lineage:**  Ogni file process.json deve registrare:

* **Timestamp:**  Data e ora UTC della trasformazione.  
* **Toolchain:**  Algoritmo esatto utilizzato (es.  *Materialize* ,  *OpenCV\_Sobel* ,  *Pillow\_LANCZOS* ).  
* **Payload Parametrico:**  Forza del filtro, convention (DX/GL), risoluzione di output.  
* **Derived\_from:**  Elenco esplicito dei file sorgente GOLD.Le varianti CUSTOM (downscaling, conversioni di formato) devono essere tracciate in modo da permettere il confronto tra risoluzioni per l'analisi della perdita di dettaglio, ma non devono mai essere confuse con la sorgente originale.

#### 4\. Procedure di Prevenzione della Contaminazione

Il rischio di "contaminazione ricorsiva" — dove l'IA apprende dai propri errori sintetici — deve essere neutralizzato dal  **Validation Gate**  del sistema.

##### Regole di Rigetto (Validation Gate)

Il sistema deve rigettare automaticamente asset che violano le seguenti soglie fisiche:

* **Normal Map:**  Devono essere in Tangent Space. Canale Blu dominante con media (mean)  **\> 140** . Mappe in scala di grigi sono causa di rigetto immediato.  
* **Albedo Energy Compliance:**  Nessun pixel può avere valore sRGB  **\< 5**  o  **\> 250**  per più dello  **0.5%**  dell'area totale (clipping prevent). Shadow/light embedding rilevati tramite FFT portano al flag di revisione.  
* **Metallic Binary Check:**  Almeno l' **80%**  dei pixel deve essere vicino ai valori estremi (0 o 255). Valori medi eccessivi indicano una mappa non fisica.

##### Isolamento dei Dati Sintetici

Ogni asset SYNTHETIC deve essere marcato come tale nel material\_info.json. I dati sintetici possono essere usati per la "Data Augmentation" ma hanno  **zero autorità**  come Ground Truth. Non possono influenzare le metriche di validazione delle prestazioni di SIGNUM SENTINEL.

#### 5\. Specifiche Tecniche e Schemi Metadati

L'interoperabilità tra Ingestor, Analyzer e Dataset Builder è vincolata all'uso dello schema JSON canonico.

##### Struttura del material\_info.json

Il file deve essere diviso in tre blocchi logici:

1. **Identity:**  material\_name, provider, source\_url (mandatorio), technique (Photogrammetry/Procedural/AI), category.  
2. **Tags:**  Elenco di tag fisici e semantici estratti dal fornitore o tramite AI vision.  
3. **Hierarchy:**  Distinzione netta tra varianti RAW (originali) e varianti CUSTOM (derivate).

##### Requisiti Tecnici dei File Immagine

* **Bit-depth:**  Obbligo di distinguere tra 8-bit e 16-bit. L'upscaling fittizio di bit-depth deve essere rilevato e segnalato.  
* **Spazio Colore:**  sRGB mandatorio per Albedo; Linear mandatorio per Normal, Roughness, Metallic, AO e Height.  
* **Validazione Exif:**  Ogni risoluzione dichiarata deve essere verificata tramite  **ExifTool**  per prevenire "fake upscales".

#### 6\. Il Physics Oracle e la Validazione Finale

Il  **Physics Oracle (Layer 0\)**  è il garante supremo della plausibilità fisica. Esso fornisce i range di riferimento estratti dalle banche dati spettrometriche (IOR, F0) che alimentano il Validation Gate.

##### Protocollo di Confronto e Profili Oracle

Il sistema deve validare i materiali confrontandoli con i seguenti profili predefiniti:

* **Profilo Dielectric:**  Albedo sRGB in range  **30, 240** , riflessione speculare (F0) fissa a  **0.04** , metallicità attesa  **0** .  
* **Profilo Metal:**  Albedo sRGB elevato  **180, 255** , metallicità attesa  **1** . Validazione tramite tabelle IOR specifiche (es. Rame, Oro).  
* **Profilo Organic:**  Range di riflettanza personalizzati basati su materiale (Legno, Terra).

##### Azioni del Decision Layer

In caso di incongruenza rilevata dall'Oracle, il  **Decision Layer**  deve eseguire azioni correttive deterministiche:

* flip\_green\_channel: Se rileva convention Normal errata (DX vs GL).  
* increase\_roughness\_contrast: Se la mappa è troppo piatta per il profilo rilevato.  
* flag\_human\_review: Blocco dell'asset per ispezione manuale.  
* purge\_asset: Rimozione definitiva se l'integrità fisica è irrimediabilmente compromessa.L'osservanza di questo protocollo non è opzionale. Ogni deviazione sarà considerata un fallimento sistemico dell'integrità di SIGNUM SENTINEL.

