# PBR MASTER KNOWLEDGE BASE — MODULO DI INTEGRAZIONE TOTALE
## PARTE B — Sezione 4: Logica Procedurale e Pipeline (Agnostica)
**Versione: 2.0-TOTAL | Data: 2026-04-12 | Continuazione da Parte A**

---

## [SEZIONE 4] LOGICA PROCEDURALE E PIPELINE (AGNOSTICA)

> Questa sezione descrive la logica operativa per la creazione, validazione e ottimizzazione
> di materiali PBR. È completamente agnostica rispetto al software: nessun menu, nessun
> pulsante, nessun percorso di tool specifico. Solo la logica sottostante e le regole fisiche
> che la governano.

---

### 4.1 Texel Density — Scala Reale e Coerenza

#### Definizione

La **texel density** (densità dei texel) descrive quanti pixel di texture corrispondono a una unità di misura reale sulla superficie di un oggetto.

$$TexelDensity = \frac{TextureResolution_{px}}{RealWorldSize_{m}}$$

Unità di misura standard: **px/m** (pixel per metro) o **px/cm** (pixel per centimetro).

*Fonte: Allegorithmic PBR Guide Vol. 2, p. 11; Google Doc "Scale e Texel Density"; Google Doc "Framework PBR Training v1"*

#### Standard di Produzione

| Contesto | Texel Density | Note |
|:---------|:-------------|:-----|
| Standard produzione (target) | **1024 px/m** (10.24 px/cm) | Baseline per la maggior parte degli asset |
| Hero asset (oggetti ravvicinati, interattivi) | **2048 px/m** | Personaggi, armi, oggetti principali |
| Architettura / large scale | **256–512 px/m** | Edifici, terreni, fondali |
| Detail map (overlay tileable) | N/A (tileable, non assoluta) | La densità è relativa al tiling factor |

*Fonte: Google Doc "Scale e Texel Density"; DVAMOCLES Spec v3.1-FINAL §9.5; DOMANDE_PER_LA_PARTE_2*

#### Conseguenza di Incoerenza

Se oggetti adiacenti nella stessa scena hanno texel density molto diverse, l'occhio umano percepisce una discrepanza di qualità fastidiosa. Un tavolo con 512 px/m e una tazzina con 2048 px/m appaiono visivamente incongruenti, indipendentemente dai valori corretti di albedo o roughness.

**Regola operativa**: la texel density deve essere coerente tra tutti gli oggetti visibili contemporaneamente nella stessa scena. Un'errore di scala del 20% o superiore è percepibile e classificabile come errore di produzione.

*Fonte: Google Doc "Framework PBR Training v1", Sezione 5*

#### Cheat Sheet — Dimensioni Reali dei Materiali

*Fonte: Google Doc "Scale e Texel Density"; standard edilizi internazionali*

| Materiale | Dimensione Reale | Note Pratiche |
|:----------|:----------------|:-------------|
| **Mattone Standard** | 21 cm × 6 cm (elemento) | Con fuga: ~22 × 7 cm. IRL: 215 × 102.5 × 65 mm |
| **Piastrella bagno small** | 30 × 30 cm | Fuga: 2–3 mm |
| **Piastrella bagno large** | 60 × 60 cm | Fuga: 2–3 mm |
| **Tessuto (trama fibra)** | 1–2 mm per fibra | Richiede Detail Normal ad alta frequenza |
| **Tavola parquet** | 10–15 cm (larghezza), 100–200 cm (lunghezza) | Vena del legno lungo la lunghezza |
| **Cemento / intonaco** | Pattern macro: 5–20 cm | Micro-dettaglio: porosità ~1–5 mm |
| **Asfalto** | Granuli: 5–20 mm | Texture tileable su area ~1m × 1m |
| **Roccia (granito)** | Cristalli: 1–10 mm | Variabile per tipo |

#### Calcolo Pratico

**Esempio**: muro di mattoni, texture 2048×2048, dimensione reale del tile 88 cm × 60 cm (4 mattoni × 3 file):

$$TexelDensity = \frac{2048 px}{0.88 m} \approx 2327 \, px/m$$

Questo supera il target standard di 1024 px/m → adeguato per un muro hero o ravvicinato; per uno sfondo si potrebbe ridurre a 1024×1024.

---

### 4.2 Frequenza del Dettaglio — Tre Livelli

Ogni materiale reale presenta variazioni visive a scale diverse. I renderer PBR gestiscono queste frequenze separatamente.

| Livello | Scala | Contenuto | Mappa PBR |
|:--------|:------|:----------|:----------|
| **Macro** | Variazioni di area (cm–m) | Macchie di usura, variazioni cromatiche, AO larga, pattern di colore | Base Color (bassa frequenza), AO |
| **Medium** | Pattern ripetuto (mm–cm) | I singoli mattoni, le fibre del tessuto, la grana del legno | Normal, Height, Base Color (media freq.) |
| **Micro** | Struttura superficiale (µm–mm) | Porosità, grana del metallo, micro-graffi, rugosità fine | Detail Normal, Roughness (alta freq.) |

**Regola del Detail Normal Map**: per preservare il micro-dettaglio visibile ravvicinato senza aumentare indefinitamente la risoluzione base, si sovrappone una **Detail Normal Map** tileable ad alta frequenza (tiling factor 4–16× rispetto alla texture base). Il micro-dettaglio rimane nitido a qualsiasi distanza di avvicinamento.

*Fonte: Google Doc "Scale e Texel Density"; DVAMOCLES Spec v3.1-FINAL §9.1 (Detail Map 3-in-1)*

---

### 4.3 Creazione delle Mappe — Logica Agnostica

#### 4.3.1 Base Color / Albedo

**Obiettivo**: rappresentare il colore diffuso della superficie, privo di informazioni di illuminazione.

**Logica di creazione**:
1. La texture base NON deve contenere ombre, AO, riflessi o qualsiasi informazione di luce direzionale
2. I valori devono rimanere nel range fisicamente plausibile (§3.4)
3. La micro-occlusione contestuale (crepe, fessure molto strette) è l'unica eccezione ammessa: può essere integrata nell'albedo quando la risoluzione della shadow map non è sufficiente a catturare quel livello di dettaglio
4. Per i metalli: il Base Color contiene i valori F0 (§3.2), non un colore diffuso

**Errori critici da evitare**:
- Multiply dell'AO sull'albedo (produce macchie scure permanenti che non reagiscono all'illuminazione diretta)
- Saturazione eccessiva (colori impossibili fuori dal gamut fisico)
- Valori sotto 30 sRGB per dielettrici comuni (eccezione: carbone, pneumatico, MIT Black)
- Valori sopra 240 sRGB per dielettrici comuni (eccezione: neve fresca, Spectralon)

*Fonte: Allegorithmic PBR Guide Vol. 2, pp. 6-7; Google Doc "Quality Control"*

#### 4.3.2 Normal Map

**Obiettivo**: modificare la direzione delle normali superficiali per simulare dettaglio geometrico senza aumentare il conteggio dei poligoni.

**Logica di creazione**:
1. La Normal Map lavora in **tangent space**: ogni pixel è un vettore relativo alla normale locale della superficie
2. Il valore neutro (superficie piatta) è: R=128, G=128, B=255 in sRGB 8-bit → che corrisponde al vettore normalizzato (0, 0, 1) in spazio lineare
3. Il canale B è sempre positivo (la normale punta "verso fuori" dalla superficie)

**Derivazione da Height Map**:
La Normal Map può essere calcolata come gradiente della Height Map:

$$N_x = \frac{\partial H}{\partial x}, \quad N_y = \frac{\partial H}{\partial y}, \quad N_z = \text{costante positiva}$$

Poi il vettore $(N_x, N_y, N_z)$ viene normalizzato e codificato nel range [0, 1] per la texture.

**Conversione di formato (GL ↔ DX)**:
Per convertire una Normal Map da OpenGL a DirectX (o viceversa):
- Invertire il **canale Verde (G)**: $G_{DX} = 1.0 - G_{GL}$
- I canali R e B rimangono invariati

**Normalizzazione**:
I vettori devono soddisfare: $\sqrt{R^2 + G^2 + B^2} = 1$ (in spazio lineare normalizzato)
- Se la lunghezza del vettore si discosta da 1.0 di più di ±0.05, il pixel è "corrotto" e produrrà shading errato

**Compressione BC5**: il canale B viene omesso e ricostruito matematicamente dal renderer:
$$B = \sqrt{1 - R^2 - G^2}$$
Questo funziona perché le normali in tangent space hanno sempre B > 0.

*Fonte: Allegorithmic PBR Guide Vol. 2, pp. 21; Google Doc "Framework PBR Training v1"; PBR_MKB_Part1 §8.2*

#### 4.3.3 Roughness

**Obiettivo**: descrivere la distribuzione delle microfaccette superficiali (§2.3).

**Logica di creazione**:
- È la mappa più "creativa": non ha vincoli fisici stretti come albedo o metallic
- Un buon punto di partenza è la Normal Map stessa: le aree con alto dettaglio normale spesso hanno roughness più elevata (micro-solchi, porosità)
- Evitare valori estremi (0.0 o 1.0 puro) su aree estese senza giustificazione fisica
- La roughness varia a tutte le scale di frequenza (macro, medium, micro)

**Relazione con Glossiness**: $Roughness = 1.0 - Glossiness$ (in spazio lineare)

**Range fisici di riferimento**:

| Superficie | Roughness |
|:-----------|:---------|
| Specchio ottico, vetro lucidato | 0.00–0.05 |
| Metallo lucidato, ceramica lucida | 0.05–0.15 |
| Metallo lavorato/spazzolato | 0.15–0.40 |
| Plastica semilucida, legno verniciato | 0.10–0.30 |
| Legno levigato | 0.40–0.60 |
| Legno grezzo, mattone | 0.60–0.85 |
| Cemento, pietra non levigata | 0.70–0.95 |
| Tessuto, carta, terra | 0.75–1.00 |
| Acqua (superfice piatta) | 0.00–0.05 |
| Asfalto bagnato | 0.05–0.15 (riduzione dinamica) |

*Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md; appendice integrativa*

#### 4.3.4 Metallic

**Obiettivo**: indicare allo shader quali aree trattare come metallo conduttore.

**Logica**:
- Mappa grayscale, idealmente **binaria**: 0 (dielettrico) o 1 (metallo puro)
- I valori intermedi (0.1–0.9) sono fisicamente giustificati solo per transizioni graduale di ossidazione, sporco o vernice parzialmente rimossa
- **Errore comune**: usare grigio medio (0.5) come valore di default → non esiste fisicamente un materiale "mezzo metallo"

**Regole operative** *(Fonte: Allegorithmic PBR Guide Vol. 2, p. 7-9)*:
1. Raw metal puro: Metallic ≥ 235 sRGB (≈ 0.85 lineare) — spesso 1.0 puro
2. Transizione ossidazione/sporco: Metallic può scendere gradualmente verso 0
3. Ruggine: Metallic = 0 (la ruggine è un ossido → dielettrico)
4. Metallo verniciato: Metallic = 0 sulla vernice, 1 sul metallo esposto
5. Se il Metallic map ha valori < 235 sRGB, il valore di riflettanza F0 nel Base Color deve essere ridotto di conseguenza (non lasciare valori alti di albedo su aree con Metallic basso)

#### 4.3.5 Ambient Occlusion (AO)

**Obiettivo**: simulare quanto luce ambientale diffusa raggiunge ogni punto della superficie.

**Definizione fisica**: l'AO calcola la percentuale di emisfero visibile dal punto superficiale non bloccata dalla geometria circostante.

**Regola fondamentale**: l'AO influenza **solo la luce diffusa ambientale** (indirect lighting). Non deve influenzare la luce diretta e non deve influenzare la riflessione speculare.

$$AO_{effect}: \quad L_{ambient} \rightarrow L_{ambient} \times AO_{value}$$

**Errori critici**:
- Non integrare l'AO nel Base Color (moltiplicarla sull'albedo) — produce macchie scure permanenti visibili anche sotto luce diretta forte
- L'AO deve essere importata come canale separato e gestita dallo shader

**Creazione logica**:
- Dall'AO si derivano anche maschere di sporco e umidità (aree ad alta occlusione → accumulo di sporco, umidità)
- AO alta (aree scure) corrisponde a cavità e angoli interni
- La relazione con la Roughness: nelle cavità ad alta AO, la Roughness tende ad aumentare (accumulo di micro-detriti)

*Fonte: Allegorithmic PBR Guide Vol. 2, pp. 18; Google Doc "Quality Control"; Google Doc "Framework PBR Training v1" §5*

#### 4.3.6 Height Map

**Obiettivo**: rappresentare dati di elevazione per displacement o parallax mapping.

**Bit depth critica**:
- 8-bit: produce **banding** visibile sulle aree di transizione graduale (256 valori discreti insufficienti)
- 16-bit: range 0–65535 → transizioni fluide, adeguato per displacement architettonico
- 32-bit float (EXR): massima precisione, necessario per dati fotogrammetrici o scansioni

**Logica di derivazione**:
- Da mesh ad alta risoluzione → baking (proiezione sulla mesh bassa)
- Da Normal Map → integrare i gradienti per ottenere una stima dell'altezza (meno accurato)
- Da foto/scan → analisi di profondità

**Differenza Displacement vs Parallax**:
- **Parallax mapping**: la Height Map viene usata per simulare otticamente la profondità spostando le coordinate UV. Non cambia la silhouette. Computazionalmente leggero.
- **Displacement**: la Height Map sposta fisicamente i vertici della mesh. Richiede tessellazione (suddivisione della mesh). Cambia la silhouette. Molto più costoso computazionalmente.

*Fonte: Allegorithmic PBR Guide Vol. 2, pp. 19-20; Google Doc "Framework PBR Training v1" §2*

#### 4.3.7 Thickness Map

**Obiettivo**: indicare quanto spessore ha il materiale in ogni punto — usato per SSS e trasmissione.

**Valori**: 0 = spessore zero (area molto sottile, molta luce passa), 1 = spessore massimo (luce bloccata completamente).

**Uso SSS**: aree con basso valore di thickness (orecchie, dita, foglie) permettono alla luce di "trasparire" da dietro.

---

### 4.4 Layering System — Stratificazione dei Materiali

*Fonte: Google Doc "Quality Control — Layered Shading"; Google Doc "Framework PBR Training v1" §5; DOMANDE_PER_LA_PARTE_2*

#### 4.4.1 Principio della Stratificazione

Un materiale complesso non è creato da un'unica texture, ma da più **layer logici** sovrapposti che interagiscono fisicamente. Ogni layer ha il proprio set di proprietà (albedo, roughness, metallic) e viene bloccato sulla superficie sottostante tramite maschere derivate dalla geometria o da mappe procedurali.

#### 4.4.2 Gerarchia Obbligatoria dei Layer

*Dall'interno verso l'esterno (dal basso verso l'alto):*

| Ordine | Layer | Tipo di Materiale | Logica di Maschera |
|:-------|:------|:-----------------|:-------------------|
| **0** | Substrate (Base) | Materiale strutturale (metallo grezzo, pietra, cemento) | Nessuna — è il fondamento |
| **1** | Surface Treatment | Vernice, primer, ossidazione, anodizzazione | Maschera basata su Curvature (bordi esposti = usura) |
| **2** | Micro-Dettaglio | Ossidazione localizzata, graffi superficiali | Mappe di grunge procedurali |
| **3** | Ambiente | Sporco, umidità, ruggine, moss | AO (accumulo nelle concavità) + World Normal (caduta dall'alto) |
| **4** | Top Layer | Polvere, neve, umidità superficiale | World Space Normal Y+ (deposito per gravità) |

*Fonte: Google Doc "Quality Control — Layered Shading", Schema di Stratificazione*

#### 4.4.3 Height-Based Blending

Il metodo più fisicamente plausibile per mescolare due materiali è il **Height Blend**: usa la Height Map per decidere dove appare il secondo layer.

**Logica**:
- Il secondo materiale (es. fango) riempie prima le **valli** (aree scure nella Height Map del primo layer)
- Solo aumentando l'intensità del blend il secondo materiale raggiunge le **cime** (aree chiare nella Height Map)
- Questo simula il comportamento fisico reale: l'acqua e il fango si accumulano nelle depressioni

**Algoritmo semplificato**:
```
blend_mask = saturate(height_map_base + blend_amount - 0.5)
result = lerp(material_A, material_B, blend_mask)
```

**Risultato**: transizioni visivamente convincenti che seguono la topografia della superficie, invece di una sfumatura lineare artificiale.

*Fonte: Google Doc "Quality Control — Layered Shading"*

#### 4.4.4 Edge Wear — Logica dell'Usura

L'usura fisica si concentra sui **bordi esposti** della geometria: spigoli, angoli, punti di contatto e attrito.

**Maschera derivata**: mappa di **Curvatura** (Curvature Map)
- Valori positivi (convessità): bordi esposti → usura, perdita di vernice
- Valori negativi (concavità): angoli interni → accumulo di sporco

**Formula di usura base**:
$$WearMask = saturate(Curvature \times intensity + offset)$$

**Effetto sul materiale**: nelle aree di curvatura positiva alta, la vernice (Layer 1) viene rimossa, esponendo il metallo sottostante (Layer 0). Il Metallic passa gradualmente da 0 (vernice) a 1 (metallo esposto).

#### 4.4.5 Dirt Accumulation — Accumulo di Sporco

Lo sporco si deposita nelle **concavità** e nelle aree con alta occlusione ambientale.

**Formula di accumulo sporco**:
$$DirtMask = AO \times (1 - Curvature)$$

Dove:
- AO alta (0→1) indica aree nascoste alla luce → accumulo
- (1 - Curvature) rimuove lo sporco dai bordi convessi (che fisicamente vengono "puliti" da attrito)

*Fonte: Google Doc "Quality Control — Layered Shading"; appendice integrativa PBR_MKB_Part1*

#### 4.4.6 Dust/Snow Accumulation — Deposito per Gravità

Polvere e neve si depositano sulle **superfici rivolte verso l'alto**.

**Maschera derivata**: World Space Normal Y+ (o Z+ a seconda della convenzione degli assi)
$$DustMask = saturate(WorldNormal.y \times intensity)$$

**Effetto**: le facce orizzontali e inclinate verso l'alto accumulano polvere; le pareti verticali e le superfici rivolte verso il basso rimangono pulite.

#### 4.4.7 Wetness Layer — Umidità

L'umidità modifica le proprietà del materiale in modo fisicamente determinato:

| Proprietà | Effetto umidità | Motivazione fisica |
|:----------|:---------------|:-------------------|
| **Roughness** | Diminuisce (→ 0.05–0.15) | Film d'acqua livella le microfaccette |
| **Albedo** | Si scurisce (×0.7–0.85) | L'acqua assorbe parte della luce diffusa |
| **Specular F0** | Aumenta (sopra 0.04) | IOR acqua ≈ 1.333 → F0 ≈ 0.02, ma il film fa salire la riflessione) |
| **Pooling** | Acqua nelle cavità (guidato da AO + Height) | La gravità concentra l'acqua nelle depressioni |

**Maschera wetness**: derivata da AO (pozze nelle concavità) + WorldNormal.y (superfici orizzontali)

*Fonte: DVAMOCLES Spec v3.1-FINAL §9.6 (Wetness System)*

---

### 4.5 Car Paint — Materiale Multi-Layer Avanzato

*Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md; Google Doc "Framework PBR Training v1"*

La verniciatura automobilistica è l'esempio canonico di materiale con **due layer ottici sovrapposti**:

#### Struttura Fisica

```
Layer 0: Metallo/substrato
Layer 1: Basecoat (vernice pigmentata + flake metalliche)
Layer 2: Clearcoat (lacca trasparente)
```

#### Parametri per Layer

| Layer | Roughness | Metallic | Note |
|:------|:---------|:---------|:-----|
| Basecoat | 0.3–0.6 | 0 (vernice) o 1 (flake) | Flake metalliche: pattern procedurale, scala ~0.5–2mm |
| **Clearcoat** | **0.02–0.10** | 0 | Molto lucido — questo è il "shine" caratteristico |

**Regola critica**: il Clearcoat ha la sua Roughness e il suo Fresnel **indipendenti** dal Basecoat. La riflessione lucida che vediamo su un'auto è quella del Clearcoat, non del Basecoat.

**Errore comune**: usare un'unica mappa Roughness bassa per simulare la verniciatura. Risultato: appare plastica lucida, non vernice auto. La caratteristica distintiva è la compresenza di due highlight separati (Clearcoat sharp + Basecoat diffuso con flake).

---

### 4.6 LOD Strategy — Degradazione per Distanza

*Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md*

#### Principio Fisico della LOD

Il LOD (Level of Detail) non riguarda solo la geometria — in PBR, anche i materiali devono degradare con la distanza in modo fisicamente coerente. Un materiale LOD sbagliato cambia il comportamento della luce percepito dall'osservatore.

**Regola fondamentale**: semplificare la forma del dettaglio, **non il comportamento fisico della luce**.

#### Tabella LOD per Materiali PBR

| LOD | Distanza | Risoluzione | Normal | Height | Roughness | Note |
|:----|:---------|:------------|:-------|:-------|:---------|:-----|
| **LOD0** (vicino) | 0–3m | 4K | Full detail + detail normal | 16-bit | Mappa completa alta-freq | Tutte le mappe attive |
| **LOD1** | 3–10m | 2K | Normal semplificata | **Baked in normal** | Normal smoothed | Height non necessaria a questa distanza |
| **LOD2** | 10–30m | 1K | Normal ridotta | Rimossa | Roughness leggermente smoothed | Micro-dettaglio non visibile |
| **LOD3** (lontano) | 30m+ | 512px o meno | Flat o rimossa | Rimossa | **Roughness costante** | Solo albedo + roughness media |

#### Regole di Degradazione Corretta

**Mantenere invariati**:
- Range di albedo (min/max sRGB)
- Roughness media del materiale (il valore medio non cambia, solo la varianza diminuisce)
- F0 / Metallic (il tipo di materiale non cambia con la distanza)

**Ridurre progressivamente**:
- Alta frequenza nella Normal Map
- Alta frequenza nella Roughness (grana fine)
- Detail map e Height map

**Aumentare leggermente**:
- Roughness minima (+0.05–0.10) per LOD2 e LOD3: simula la perdita di informazione sulle microfaccette

**Errore**: se tra LOD0 e LOD1 il comportamento della luce cambia visibilmente (es. il metallo smette di sembrare metallo, o la roughness appare diversa), il LOD è sbagliato.

---

### 4.7 Hero Asset → Tiling: Conversione

*Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md*

#### Il Problema

Un hero asset (alta qualità, non ripetitivo) non può essere convertito direttamente in una texture tileable. La conversione 1:1 produce pattern evidenti e visivamente fastidiosi.

#### Metodo per la Conversione

**Step 1 — Separazione delle frequenze**:
- Low freq (colore macro, variazione di luminosità): rimane "world-aligned" o mappata su vertex color
- Mid freq (pattern principale: mattoni, fibre, grana): diventa la texture tileable
- High freq (porosità, micro-graffi): diventa la Detail Normal Map tileable ad alta frequenza

**Step 2 — Rendere tileable SOLO mid e high freq**

**Step 3 — Sistema di variazione** per eliminare il pattern:
- Macro variation noise (scala 0.1–0.3): varia il colore su larga scala con una noise
- UV offset random per tile: ogni tile ha un piccolo offset random per spezzare la ripetizione
- Texture blending: 2–3 varianti della stessa texture in blend procedurale
- Pattern breaking: decals, maschere procedurali, rotation 90°/flip

*Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md*

---

### 4.8 Workflow di Validazione Fisica — Sanity Check Logico

*Fonte: appendice integrativa; DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md; Allegorithmic Vol. 2; Google Doc "Quality Control"*

#### 4.8.1 Struttura del Sanity Check a 3 Livelli

Il sanity check PBR si articola in tre livelli di severità:

| Livello | Nome | Tipo | Azione |
|:--------|:-----|:-----|:-------|
| **L1** | Visual Runtime | Sempre attivo durante editing | Feedback visivo (istogramma live), non blocca |
| **L2** | Pre-Export Gate | Attivato all'export | Lista violazioni → richiede conferma consapevole |
| **L3** | Auto-Fix | Opzionale | Normalizza automaticamente i valori fuori range |

#### 4.8.2 Soglie di Validazione per Canale

**Base Color / Albedo (dielettrici)**:

| Check | Soglia | Severità | Note |
|:------|:-------|:---------|:-----|
| Min albedo | < 30 sRGB | ERROR | Fisicamente non plausibile eccetto carbone/pneumatico |
| Min albedo strict | < 50 sRGB | WARNING | Range tolerant (30–50) vs strict (50–240) |
| Max albedo | > 240 sRGB | WARNING | Plausibile solo per neve/Spectralon |
| Zero assoluto | = 0 sRGB | ERROR | Inesistente in natura eccetto MIT Black |

**Base Color per Metalli**:

| Check | Soglia | Severità | Note |
|:------|:-------|:---------|:-----|
| Min reflectance metallo | < 180 sRGB (~ 0.5 lineare) | ERROR | Metallo con F0 < 50% non è un metallo puro |
| Diffuse color su metallo | Luminosità alta con Metallic=1 | WARNING | I metalli puri non hanno albedo diffusa colorata |

**Metallic**:

| Check | Soglia | Severità | Note |
|:------|:-------|:---------|:-----|
| Valore non binario | 0.1 < Metallic < 0.9 | WARNING | Fisicamente sospetto, ma ammesso per ossidazione |
| Valore grigio medio | Metallic ≈ 0.5 su area estesa | ERROR | Non esiste fisicamente un "mezzo metallo" |

**Roughness**:

| Check | Condizione | Severità | Note |
|:------|:----------|:---------|:-----|
| Spike a 0.0 | Area estesa con Roughness = 0.0 | WARNING | Specchio perfetto — raro in natura |
| Spike a 1.0 | Area estesa con Roughness = 1.0 | WARNING | Superficie completamente assorbente — verificare |
| Distribuzione anomala | Bimodale estrema (tutto 0 o tutto 1) | ERROR | Indica una mappa di Glossiness importata come Roughness |

**Normal Map**:

| Check | Soglia | Severità | Note |
|:------|:-------|:---------|:-----|
| Normalizzazione | $|N| \neq 1.0 \pm 0.05$ | ERROR | Vettore non normalizzato → shading errato |
| Valore neutro anomalo | R, G != 128 in aree piatte | WARNING | Possibile errore di conversione gamma |
| Cluster RGB strani | Distribuzione anormale canali | WARNING | Segnale di artefatto o mappa errata |
| Seams visibili | Discontinuità ai bordi UV | ERROR | Padding insufficiente o baking errato |

*Fonte: appendice integrativa; DOMANDE_PER_LA_PARTE_2 "Sanity Check automatico"*

#### 4.8.3 Pseudo-Logica del Sanity Check Automatico

*(Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md — adattato a logica agnostica)*

```python
# Base Color validation (dielettrici, Metallic == 0)
if albedo_min < 30:   → ERROR: "Albedo sotto soglia fisica minima"
if albedo_max > 240:  → WARNING: "Albedo sopra soglia fisica massima"

# Metallic validation
if 0.1 < metallic_value < 0.9:
    if large_area:    → ERROR: "Metallic non binario su area estesa"
    else:             → WARNING: "Metallic intermedio (ossidazione?)"

# Roughness validation
if roughness distribution is bimodal extreme:
                      → ERROR: "Possibile Glossiness importata come Roughness"

# Normal Map validation
if |vector_length - 1.0| > 0.05:
                      → ERROR: "Normale non normalizzata"
if green_channel_inverted:
                      → WARNING: "Possibile formato GL/DX errato"

# Cross-check Metal + Base Color
if metallic > 0.9 and albedo_luminance < 0.50:
                      → WARNING: "Metallo con reflectance troppo bassa"
```

#### 4.8.4 Validazione della Correlazione Cross-Map

*Fonte: Google Doc "Framework PBR Training v1" §1*

Le mappe non sono indipendenti. Il sanity check avanzato verifica le correlazioni:

| Correlazione | Attesa | Flag se violata |
|:-------------|:-------|:----------------|
| Normal ↔ Height | La Normal è il gradiente della Height | Divergenza forte tra dettagli |
| Roughness ↔ AO | Nelle cavità (alta AO), roughness tende ad aumentare | Roughness bassa in zone alta AO |
| Metallic ↔ Base Color | Se Metallic=1, Base Color = reflectance (180–255 sRGB) | Metallic=1 con Base Color < 50 sRGB |
| Metallic ↔ Albedo | Se Metallic=0, Base Color = albedo diffusa | Metallic=0 con Base Color troppo scuro |

---

### 4.9 Matrici di Dipendenza delle Mappe (Map Interdependency)

*Fonte: Google Doc "Framework PBR Training v1" §1; Google Doc "Archive PBR Training"*

Le mappe PBR non sono indipendenti — esistono relazioni fisiche e percettive tra di esse. Un materiale coerente rispetta queste correlazioni.

#### Matrice Dipendenze Primarie

```
Normal ←→ Height
  La Normal Map è il gradiente della Height Map.
  Ogni variazione di altezza genera una variazione di normale.
  Un bump nella Height senza corrispondente variazione nella Normal produce
  shading incoerente (oggetto "piatto" con displacement).

Roughness ←→ AO
  Nelle zone di alta occlusione (cavità, fessure), la Roughness aumenta
  per effetto dell'accumulo di micro-detriti.
  Una Normal Map con alta frequenza in una zona implica micro-detriti
  → Roughness localmente più alta.

Metallic ←→ Base Color
  Se Metallic = 1: Base Color = F0 (riflettanza speculare)
  Se Metallic = 0: Base Color = Albedo (riflessione diffusa)
  Questi due contenuti sono fisicamente incompatibili sullo stesso pixel.
  La maschera Metallic decide quale interpretazione usare.

Curvature → Wear Mask
  Curvature positiva (bordi convessi) → area di usura potenziale
  Curvature negativa (concavità) → area di accumulo sporco

AO → Dirt/Moisture Mask
  Alta AO = area nascosta = accumulo sporco/umidità

WorldNormal.Y → Dust/Snow Mask
  Normali verso l'alto = superfici orizzontali = deposito per gravità

Height → Pooling Mask
  Valli nella Height = zone di accumulo acqua/fango
```

---

### 4.10 Workflow Fotogrammetria — Preprocessing PBR

*Fonte: DVAMOCLES Spec v3.1-FINAL §13; appendice integrativa*

Le texture ottenute da fotogrammetria o scansione fotografica contengono illuminazione baked che deve essere rimossa prima di usarle in un renderer PBR.

#### Problemi Tipici nelle Texture Fotogrammetriche

| Problema | Causa | Soluzione |
|:---------|:------|:---------|
| **Illuminazione baked** | Foto scattate con illuminazione direzionale | Delighting (rimozione shadow/highlight) |
| **Color spill** | Riflessioni colorate da oggetti adiacenti | Albedo Uniformity — livellamento cromatico |
| **Range albedo errato** | Sovra/sottoesposizione | Mappatura nel range fisico corretto |
| **Gamma errata** | Workflow non-lineare | Normalizzazione spazio colore |
| **Artefatti di compressione** | Formato JPEG nella catena di acquisizione | Scartare il materiale o correggere manualmente |

#### Procedura di Preprocessing (Agnostica)

1. **Analisi dell'illuminazione**: identificare la direzione e il tipo di luce nelle foto (luce direzionale, diffusa, mista)
2. **Delighting base**: analisi della luminanza → appiattimento delle ombre portate (deterministic luminance analysis)
3. **Albedo Uniformity**: livellamento dei valori cromatici tra foto scattate in condizioni diverse
4. **Color space normalization**: conversione nel profilo corretto (sRGB per Base Color, Linear per dati)
5. **Artifact Detection**: flagging automatico di anomalie (saturazione eccessiva, zone di sfocatura, artefatti JPEG)
6. **Validazione range finale**: applicare sanity check (§4.8) al risultato

#### Scope MVP vs Avanzato

| Funzione | MVP | Avanzato (AI-dipendente) |
|:---------|:----|:-------------------------|
| Shadow flattening deterministic | ✅ | — |
| Albedo uniformity | ✅ | — |
| Artifact detection | ✅ | — |
| Color space correction | ✅ | — |
| Full delighting (direzionale) | ❌ | ✅ AI Tier 3 |
| Normal reconstruction da foto | ❌ | ✅ AI Tier 3 |
| Seam fixing | ❌ | ✅ AI Tier 3 |

---

### 4.11 Workflow Materiali Traslucidi — Vetro, Acqua, Plastica Trasparente

*Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md; Google Doc "Framework PBR Training v1"*

Il workflow Metal/Roughness standard **non è sufficiente** per materiali con trasmissione significativa della luce.

#### Tipologie di Trasmissione

| Tipo | Descrizione | Shader necessario |
|:-----|:-----------|:------------------|
| **Thin-Walled (Bolla)** | Oggetto senza spessore significativo (es. vetro sottile) | Solo riflessione Fresnel, nessuna rifrazione volumetrica |
| **Volumetrico** | Oggetto con spessore che devia la luce | Refraction shader con IOR + absorption |
| **SSS** | Luce scattera internamente | BSSRDF con scatter distance |

#### Parametri Chiave per Trasparenti

| Materiale | IOR | Modalità |
|:----------|:----|:---------|
| Acqua | 1.333 | Volumetrico |
| Vetro comune | 1.52 | Volumetrico o thin-walled |
| Diamante | 2.417 | Volumetrico + dispersione |
| Plastica trasparente | 1.46–1.59 | Thin-walled o volumetrico |

**Regola**: non forzare vetro o plastica trasparente nel workflow Metal/Roughness standard con semplice bassa roughness. Il risultato sarà plastica riflettente, non vetro trasparente.

---

### 4.12 Anisotropia — Workflow per Metallo Spazzolato

*Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md; Google Doc "Compendio Tecnico PBR"*

#### Quando Usare Anisotropia

- Metallo spazzolato (acciaio, alluminio satinato)
- Capelli e pellicce
- Seta e tessuti con lucentezza direzionale
- Fondi di pentole in acciaio
- Dischi in vinile

#### Dati Necessari

1. **Roughness map** (standard)
2. **Anisotropy Amount** (0 = isotropo, 1 = massima anisotropia)
3. **Anisotropy Rotation / Tangent map** (orienta la direzione dei solchi)

#### Effetto Visivo

L'highlight speculare non è circolare ma si allunga nella direzione **perpendicolare** ai solchi:
- Solchi orizzontali → highlight allungato verticalmente
- Solchi a 45° → highlight ruotato a 45°

---

### 4.13 Clear Coat — Workflow Doppio Strato

*Fonte: Google Doc "Framework PBR Training v1"; DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md*

#### Struttura Fisica

Il Clear Coat è uno strato di lacca/resina trasparente sopra il materiale base. Ha proprietà ottiche indipendenti:

| Proprietà | Base Material | Clear Coat |
|:----------|:-------------|:-----------|
| Roughness | 0.3–0.6 (tipico) | **0.02–0.10** (molto basso) |
| F0 | Dal materiale base | 0.04 (dielettrico trasparente standard) |
| IOR | Dal materiale base | ~1.5 (lacca standard) |

#### Comportamento Ottico

Quando la luce colpisce una superficie con Clear Coat:
1. Una parte viene riflessa dal Clear Coat (highlight nitido, low roughness)
2. Una parte penetra attraverso il Clear Coat e interagisce con il Base Material
3. Doppio highlight caratteristico: uno sharp (Coat) + uno diffuso o metallico (Base)

#### Materiali con Clear Coat

- Carrozzerie auto
- Mobili laccati
- Strumenti musicali (chitarre)
- Bulbi oculari (umidità superficiale)
- Ceramica smaltata

---

### 4.14 Materiali SSS — Implementazione Pratica

*Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md; Allegorithmic PBR Guide Vol. 1 §Absorption and Scattering*

#### Materiali che Richiedono SSS

| Materiale | Scatter Distance | Note Pratiche |
|:----------|:----------------|:-------------|
| **Pelle umana** | 1–3 mm | Rosso viaggia più lontano → orecchie/dita rosse in controluce |
| **Marmo** | 5–20 mm | SSS molto visibile, specie in controluce |
| **Latte** | 10–50 mm | Partecipating medium completo |
| **Cera** | 2–10 mm | |
| **Foglie** | 0.5–2 mm | Translucency visibile in controluce |
| **Giada** | 3–8 mm | |

#### Prevenire il "Waxy Look"

Il "waxy look" (aspetto ceroso innaturale) è l'errore più comune con SSS:

| Causa | Correzione |
|:------|:----------|
| Scatter distance troppo alta | Ridurre a valori fisici corretti (§3.5) |
| Roughness troppo bassa in combinazione con SSS | Aumentare roughness a 0.3–0.5 |
| SSS color troppo saturo | Usare il colore reale della pelle/materiale (dal database §3.3) |
| Assenza di micro-dettaglio (pori, variazione) | Aggiungere Roughness variation map |

#### Il Canale Rosso della Pelle

La pelle umana scattera la luce in modo cromaticamente diverso per canale:
- **Rosso**: viaggia più lontano (1–3 mm) — prodotto dall'emoglobina
- **Verde**: media distanza (~0.5–1 mm)
- **Blu**: distanza minima (~0.2–0.5 mm)

Questo spiega perché le orecchie e le dita appaiono rossastre quando retroilluminate.

---

### 4.15 Spazio Colore Avanzato — ACEScg e Pointer's Gamut

*Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md*

#### ACEScg vs sRGB

| Aspetto | sRGB | ACEScg |
|:--------|:-----|:-------|
| Tipo | Display-referred | Scene-referred (linear, wide gamut) |
| Gamma | ~2.2 | 1.0 (lineare) |
| Gamut | Relativamente stretto | Molto più ampio del sRGB |
| Uso | Export finale, monitor | Working space in pipeline VFX/AAA |
| Albedo in ACES | Gamma encoded | **Più ampia gamma possibile** |

**Regola operativa**: lavorare sempre in linear space. Convertire a sRGB o ACES solo all'output finale. Le texture di albedo create in ACES avranno valori diversi rispetto a sRGB per lo stesso materiale fisico.

#### Pointer's Gamut

Il **Pointer's Gamut** è il gamut delle superfici reali misurate nel mondo fisico (misurazione di ~4000 campioni di colori materiali naturali).

**Significato per PBR**: i colori fisicamente possibili per l'albedo di un materiale reale sono contenuti all'interno del Pointer's Gamut. Colori molto saturi fuori da questo gamut non esistono in natura (nella maggior parte dei casi).

**Uso pratico**: clampare i colori di albedo all'interno del Pointer's Gamut previene colori "impossibili" che violano la fisica.

#### Optical Brighteners (OFP)

La carta da ufficio (e molti tessuti bianchi) contiene optical brighteners: composti che assorbono luce UV e la ri-emettono nel visibile (blu). Questo produce il comportamento anomalo nel canale B della carta da ufficio già documentato in §3.3.

**Soluzione per rendering corretto**:
- Non trattare come semplice albedo
- Aggiungere un termine emissive leggero nel canale blu
- Oppure usare shader custom con supporto UV

---

### 4.16 OpenPBR e MaterialX — Standard Emergenti

*Fonte: Valori_IOR doc; Tecnologie_limitrofe doc; DOMANDE_PER_LA_PARTE_2*

#### OpenPBR

**OpenPBR** (2025, Academy/Adobe/ILM) è un'estensione del modello PBR standard che introduce:
- Separazione esplicita di **F0** e **F90** come parametri indipendenti
- Layering fisico nativo (non approssimato)
- Supporto nativo per dispersione cromatica, thin-film, SSS in un unico modello coerente

**Parametri chiave OpenPBR** rispetto al Metal/Roughness standard:

| Metal/Roughness Standard | OpenPBR Equivalente |
|:------------------------|:-------------------|
| Base Color | Diffuse Albedo (Metallic=0) + Specular Color (Metallic=1) |
| Metallic (0/1) | Slab type (Dielectric/Conductor) |
| Roughness | Specular Roughness |
| Specular (override F0) | F0 diretto |
| — | **F90** (nuovo — riflettanza grazing angle) |
| — | **Coat** parameters (nativo) |
| — | **Fuzz** parameters (SSS/Sheen nativo) |

**Adozione attuale**: Substance Designer 15.0 (2026) ha introdotto nodi OpenPBR. I renderer principali stanno convergendo su questo standard.

#### MaterialX

**MaterialX** è uno standard open-source (ILM, 2012) per grafi di shader portabili tra tool e renderer. Usa un formato XML/JSON per descrivere reti di nodi shader in modo indipendente dal renderer.

**Vantaggi per pipeline multi-engine**:
- Un file `.mtlx` può essere usato in UE5 (via Interchange), Unity (via Needle/ShaderGraph), Arnold, RenderMan
- Supporta StandardSurface e OpenPBR
- Compatibile con USD (Universal Scene Description)

**Flusso di integrazione**:
```
Substance/Houdini → Export .mtlx → 
  ├── UE5 (Interchange plugin)
  ├── Unity (Needle exporter)
  └── Arnold/RenderMan (nativo)
```

**Limitazioni attuali**: supporto UDIM non completo in alcune implementazioni; non tutti i nodi MaterialX sono supportati in UE5 (subset Interchange).

*Fonte: Valori_IOR doc; https://materialx.org/ThirdPartySupport.html*

#### UE5 Substrate

**Substrate** (UE5.5+ beta, production-ready in UE5.7) sostituisce il sistema di shading fisso di UE5 con un framework modulare basato su "slab" di materia.

**Mapping dal workflow Metal/Roughness classico a Substrate**:

| Metal/Roughness | Substrate |
|:----------------|:---------|
| Base Color | Diffuse Albedo |
| Metallic (0/1) | Slab type (Dielectric/Conductor) |
| Roughness | Roughness (invariato) |
| Specular (F0 override) | F0 diretto |
| — | F90 (nuovo) |
| Clearcoat layer | Vertical Layer Operator (nativo) |

**Impatto sul workflow ORM**:
Substrate **mantiene compatibilità** con le texture legacy ORM. Il nodo "Substrate Shading Model" converte automaticamente gli input classici (BaseColor, Roughness, Metallic) in parametri Substrate senza modificare i file texture.

**Stato di adozione** (al 2026): production-ready da UE5.7, abilitato di default in nuovi progetti DX12, fallback su piattaforme low-end.

**Implicazioni per tool terze parti** (Substance, DVAMOCLES):
- Substance Painter esporta con template "Unreal Engine 5 Packed" (ORM) — compatibile via conversione automatica
- Non esiste ancora un template nativo Substrate in Substance
- Adobe privilegia OpenPBR su Substrate proprietario

*Fonte: Tecnologie_limitrofe doc; DVAMOCLES Spec v3.1-FINAL §SECTION-R11*

---

### 4.17 Packed Maps — Ottimizzazione Channel Packing

*Fonte: PBR_MKB_Part1 §8.8; DVAMOCLES Spec v3.1-FINAL §9.1; Allegorithmic PBR Guide Vol. 2*

Il channel packing combina più canali di dati in un'unica texture RGBA, riducendo il numero di sampler fetch a runtime.

#### Schemi di Packing Comuni

| Schema | R | G | B | A | Uso |
|:-------|:--|:--|:--|:--|:----|
| **ORM** | AO | Roughness | Metallic | — | Unity HDRP MaskMap standard |
| **RMA** | Roughness | Metallic | AO | — | Variante comune |
| **ORM+A** | AO | Roughness | Metallic | Custom | UE5 MaterialControl |
| **BC5 Normal** | Normal X | Normal Y | (ricostruito) | — | Standard Normal Map ottimizzata |
| **Detail Map 3-in-1** | MicroNormal X | MicroNormal Y | MicroRoughness | — | DVAMOCLES Detail Map standard |

#### Regole di Packing Critiche

1. **Tutti i canali in una packed map devono essere Linear/Raw** — nessuna interpretazione sRGB
2. **BC5 per Normal Map**: preserva R e G, ricostruisce B mathematicamente → perdita zero per le normali
3. **BC7 per packed RGBA**: unico formato che preserva qualità su tutti e 4 i canali (BC3/DXT5 è inferiore)
4. **Detail Map 3-in-1 richiede BC7 obbligatoriamente**: BC5 comprimerrebbe solo R+G, perdendo il canale B (MicroRoughness)

*Fonte: DVAMOCLES Spec v3.1-FINAL §9.1 (Detail Map); PBR_MKB_Part1 §10*

---

### 4.18 Errori di Shading — Diagnosi e Correzione

*Fonte: Google Doc "Quality Control"; Allegorithmic PBR Guide Vol. 2 (Appendice)*

#### Tabella Diagnosi Completa

| Sintomo Visivo | Causa Probabile | Diagnosi | Correzione |
|:--------------|:----------------|:---------|:-----------|
| **Oggetto brilla troppo ai bordi** | Roughness troppo bassa, Fresnel errato | Roughness < 0.05 su area estesa | Aumentare il valore minimo di Roughness |
| **Riflessi spenti / "neri"** | Metallic grigio (0.5) o Base Color troppo scuro per metallo | Metallic non binario, o F0 < 0.5 per metallo | Rendere Metallic binario; alzare Base Color per aree metalliche |
| **Ombre sembrano illuminate** | Normal Map con formato sbagliato (GL vs DX) | Canale G invertito rispetto all'engine target | Invertire canale Verde della Normal Map |
| **Aspetto plastico / artificiale** | Mancanza di micro-dettaglio, Roughness uniforme | No Roughness variation, no Detail Normal | Aggiungere noise su Roughness; aggiungere Detail Normal Map |
| **Macchie scure permanenti** | AO baked nell'Albedo | Moltiplicazione AO × Base Color | Rimuovere l'AO dall'Albedo; importarla come canale separato |
| **Superficie troppo uniforme** | No variazione di Roughness su macro scala | Roughness costante | Aggiungere Roughness variation map (grunge, usura) |
| **Tessere / discontinuità** | Padding insufficiente ai bordi UV | Seam visibili nel mip-mapping | Aggiungere dilation/padding oltre i bordi delle isole UV |
| **Allungamento della texture** | UV non proporzionali, bassa texel density | Stretching alle UV seams | Correggere UV, aumentare risoluzione |
| **Effetto cerato (waxy)** | SSS scatter troppo alto + Roughness bassa | Scatter distance eccessiva | Ridurre scatter; aumentare Roughness |
| **Metallo che sembra plastica** | Base Color troppo scuro per metallo | F0 < 0.5 (metallo fisicamente non corretto) | Alzare Base Color nel range 180–255 sRGB |
| **Colore diverso tra LOD** | LOD materiale cambia i valori fisici | Roughness media o metallic diversa tra LOD | Verificare che i valori medi rimangano invariati tra LOD |
| **Banding nella Height Map** | Height a 8-bit | Solo 256 livelli di elevazione | Convertire a 16-bit o 32-bit float |
| **Normal Map rotta su bordi** | Baking su mesh con normali smooth/hard non allineate | Mismatch tra cage e mesh low-poly | Correggere la cage di baking |

*Fonte: Google Doc "Quality Control", Tabella di Controllo Qualità; Allegorithmic PBR Guide Vol. 2, Correct/Incorrect Comparisons (pp. 28)*

---

## FINE PARTE B

> **Prossima sezione (Parte C)**: Standard Formati, Validazione Quantitativa, Compressione GPU (BC1–BC7, ASTC, KTX2), Normal Map metrics avanzate, histogram-based validation con soglie numeriche, Substrate channel impact su ORM/MaterialControl, pipeline KTX2+Basis Universal.
>
> Digitare **"continua"** per procedere con la Parte C.
