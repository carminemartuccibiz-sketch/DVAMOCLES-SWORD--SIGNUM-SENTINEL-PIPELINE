# PBR MASTER KNOWLEDGE BASE — MODULO DI INTEGRAZIONE TOTALE
## Documento Tecnico Enciclopedico — Teoria Fisica, Database, Pipeline, Validazione
**Versione: 2.0-TOTAL | Data: 2026-04-12 | Tipo: Single Source of Truth — Conoscenza PBR**
**Stato: PARTE A — Sezioni 1–3 (Fondamenti, Fisica, Database)**
**Documento agnostico da software. Indipendente da tool, motori e pipeline specifiche.**

> **Nota metodologica**: Questo documento è il rework evolutivo di `PBR_Master_Knowledge_Base_Part1.md`.
> Integra e supera il precedente documento assorbendone tutto il contenuto e espandendolo
> con le fonti allegate (Allegorithmic PBR Guide Vol. 1 & 2, physicallybased.info, SpectralDB,
> CGSociety IOR List, File Type Research, Substrate/MaterialX research, appendici operative,
> Google Docs di archivio PBR). Dove le fonti presentano dati discordanti, entrambi i valori
> sono riportati con indicazione della fonte. Nessun dato è stato omesso per brevità.

---

## STRUTTURA DEL DOCUMENTO

| Sezione | Titolo | Stato |
|---------|--------|-------|
| 1 | Tabella di Nomenclatura e Standard (Rosetta Stone) | ✅ PARTE A |
| 2 | Fisica della Luce e Modelli Matematici | ✅ PARTE A |
| 3 | Database Fisico Consolidato (IOR, Albedo, F0) | ✅ PARTE A |
| 4 | Logica Procedurale e Pipeline (Agnostica) | 📄 PARTE B |
| 5 | Standard Formati, Validazione e Tecnologie Emergenti | 📄 PARTE C |

---

## [SEZIONE 1] TABELLA DI NOMENCLATURA E STANDARD — ROSETTA STONE

### 1.1 Sinonimi dei Canali Texture

| Termine Primario | Sinonimi e Alias | Dominio / Tool | Note |
|:----------------|:----------------|:--------------|:-----|
| **Base Color** | Albedo, Diffuse Color, Diffuse Map | Universal (PBR) | Non sono identici: vedi §1.4 |
| **Roughness** | Microsurface, Micro-roughness | UE5, Substance, Blender | 0 = specchio, 1 = opaco |
| **Glossiness** | Smoothness, Gloss Map | V-Ray, Unity legacy, Corona | Inverso di Roughness |
| **Metallic** | Metalness, Metal Map, Metal Mask | UE5, Substance, Blender | Mappa in scala di grigi, binaria ideale |
| **Specular** | Specular Map, Reflectance Map, F0 Map | Spec/Gloss workflow, UE4 specularLevel | RGB per metalli, greyscale per dielettrici |
| **Ambient Occlusion** | AO, Baked AO, Occlusion Map | Universal | Solo luce indiretta/diffusa |
| **Normal Map** | Normal, Bump Normal, Tangent Normal | Universal | Diversa da Bump Map (vedi §1.5) |
| **Height Map** | Heightmap, Displacement Map (a volte) | Universal | Dato scalare di elevazione |
| **Displacement Map** | Displacement | Universal | Muove vertici reali, richiede tess. |
| **Thickness Map** | Thickness | SSS workflows | Descrive spessore per SSS |
| **Emissive** | Emissive Map, Glow Map | Universal | HDR ammesso (valori > 1.0) |
| **Opacity / Alpha** | Transparency, Alpha Map | Universal | 0 = trasparente, 1 = opaco |
| **Anisotropy** | Anisotropy Angle, Anisotropy Direction | Advanced PBR | Richiede Tangent Map |
| **Subsurface Color** | SSS Color, Scatter Color | SSS workflows | Colore della luce scatterizzata |
| **Clearcoat** | Clear Coat, Coat Roughness | Disney BRDF, UE5, Substance | Layer speculare secondario |

### 1.2 Sinonimi dei Workflow

| Workflow Primario | Alias | Componenti Chiave |
|:------------------|:------|:------------------|
| **Metal/Roughness** | Metalness Workflow, M/R, PBR Metallic | Base Color, Metallic, Roughness |
| **Specular/Glossiness** | Spec/Gloss, S/G | Diffuse, Specular, Glossiness |
| **OpenPBR** | — | F0, F90, Diffuse Albedo, Roughness (standard Academy/ILM 2025) |
| **Substrate** | UE5 Substrate | Slab-based: Diffuse Albedo, F0, F90, Roughness (UE5.5+) |
| **MaterialX** | MX, .mtlx | XML/JSON node graph, USD-compatible |

### 1.3 Sinonimi della Roughness

| Termine | Valore 0 | Valore 1 | Tool tipici |
|:--------|:---------|:---------|:------------|
| **Roughness** | Specchio (massima riflessione) | Completamente diffuso (opaco) | UE5, Blender, Substance |
| **Glossiness / Smoothness** | Completamente diffuso (opaco) | Specchio (massima riflessione) | V-Ray, Corona, Unity legacy |
| **Perceptual Roughness** | — | — | Alcune implementazioni usano perceptual roughness = sqrt(roughness) |

> **Conversione**: $Roughness = 1 - Glossiness$ (matematicamente esatta, ma attenzione alla gamma: applicare la conversione in spazio lineare)

### 1.4 Base Color vs Albedo — Distinzione Critica

Questi termini **non sono identici** nel workflow Metal/Roughness.

| Termine | Contesto dielettrici | Contesto metalli |
|:--------|:--------------------|:----------------|
| **Albedo** | Colore di riflessione diffusa (riflettanza diffusa) | Nero puro (metalli puri non hanno riflessione diffusa) |
| **Base Color** | Contiene l'Albedo | Contiene i valori di riflettanza speculare F0 |

*Fonte: Allegorithmic PBR Guide Vol. 2, p. 5; Compendio Tecnico PBR (archivio Carmine)*

In pratica: il canale "Base Color" in un workflow Metal/Roughness è un **contenitore duale** — albedo per i dielettrici, F0 per i metalli. Il shader interpreta i dati in base al valore del canale Metallic.

### 1.5 Normal Map vs Bump Map vs Height Map

| Tipo | Dati | Canali | Precisione | Silhouette | Note |
|:-----|:-----|:-------|:-----------|:-----------|:-----|
| **Bump Map** | Greyscale (intensità) | 1 (R) | Bassa | No | Metodo legacy, derivato in runtime come normale |
| **Normal Map** | Vettori tangent-space | 3 (RGB) | Alta | No | Standard moderno |
| **Height Map** | Elevazione scalare | 1 (R o L) | Media-Alta (dipende da bit depth) | Solo con displacement | Usata per parallax o displacement |
| **Displacement Map** | Elevazione per spostamento vertici | 1 o 3 (vector displacement) | Alta (16/32 bit) | **Sì** | Richiede tessellazione |
| **Vector Displacement** | Spostamento XYZ | 3 (RGB) | Alta | Sì | Permette spostamento in qualsiasi direzione |

### 1.6 Convenzioni Normal Map: OpenGL vs DirectX

| Parametro | OpenGL (GL) | DirectX (DX) |
|:----------|:-----------|:-------------|
| **Asse Y** | Y+ (verde indica alto) | Y- (verde invertito, indica basso) |
| **Canale G** | Normale | **Invertito** rispetto a GL |
| **Software/Engine** | Blender, Maya, Unity, Substance | Unreal Engine, 3ds Max, CryEngine |
| **Riconoscimento visivo** | Luce dall'alto su superfici in rilievo | Luce dal basso su superfici in rilievo |

> **Regola operativa**: se il rilievo appare invertito (un dosso sembra una buca), invertire il canale Verde (G) della Normal Map.

### 1.7 Spazi Colore

| Spazio | Gamma | Uso corretto | Uso errato |
|:-------|:------|:-------------|:-----------|
| **sRGB** | ~2.2 | Base Color, Emissive, Specular Color | Normal, Roughness, Metallic, AO, Height |
| **Linear** | 1.0 | Roughness, Metallic, AO, Height, Normal | Base Color (produrrebbe calcoli errati) |
| **ACEScg** | Linear, wide gamut | Working space in pipeline VFX/AAA | Non usare per export texture standard |
| **Raw / Non-Color** | Nessuna interpretazione gamma | Normal Map, Height Map, tutte le "data maps" | Base Color (perde informazione percettiva) |

> **Principio fondamentale**: tutti i calcoli di illuminazione avvengono in spazio lineare. Le mappe sRGB vengono convertite a lineare dallo shader prima dei calcoli, poi riconvertite a sRGB per la visualizzazione. *Fonte: Allegorithmic PBR Guide Vol. 1, pp. 11-12; Compendio Tecnico PBR*

---

## [SEZIONE 2] FISICA DELLA LUCE E MODELLI MATEMATICI

### 2.1 Il Modello del Raggio di Luce (Ray Model)

Un raggio di luce che colpisce una superficie si comporta in modo determinato:

1. **Riflessione**: il raggio è riflesso seguendo la legge della riflessione: $\theta_r = \theta_i$ (angolo di riflessione = angolo di incidenza)
2. **Rifrazione**: il raggio penetra nel secondo mezzo con direzione alterata

In PBR, la divisione fondamentale è:
- **Specular reflection** → riflessione alla superficie
- **Diffuse reflection** → luce refracted che scattera internamente e riemerge vicino al punto di entrata

*Fonte: Allegorithmic PBR Guide Vol. 1, p. 2*

### 2.2 Assorbimento e Scattering (SSS)

Quando la luce viaggia in un mezzo non omogeneo (pelle, latte, marmo):

- **Assorbimento**: l'intensità diminuisce, il colore cambia (dipende dalla lunghezza d'onda). La direzione non cambia.
- **Scattering**: la direzione cambia casualmente. L'intensità non cambia immediatamente.

Materiali con alto scattering e basso assorbimento sono "translucent media": fumo, latte, pelle, giada, marmo.

Il parametro **thickness** descrive quanto spessore il materiale ha, influenzando quanto luce viene assorbita o scatterizzata.

*Fonte: Allegorithmic PBR Guide Vol. 1, p. 3*

### 2.3 Microfacet Theory

Ogni superficie reale, a livello microscopico, è composta da piccole superfici planari orientate casualmente: le **microfaccette**. Ciascuna microfaccetta riflette la luce nella propria direzione basata sulla sua normale.

Le microfaccette con normale esattamente a metà tra la direzione della luce $l$ e la direzione di vista $v$ (il **half vector** $h$) contribuiscono alla riflessione visibile. Non tutte contribuiscono: alcune sono bloccate da:
- **Shadowing**: blocco dalla lato della sorgente luminosa
- **Masking**: blocco dal lato dell'osservatore

$$h = \frac{l + v}{|l + v|}$$

La distribuzione di queste microfaccette è descritta dal termine **D** della BRDF (vedi §2.6).

*Fonte: Allegorithmic PBR Guide Vol. 1, p. 5*

### 2.4 Conservazione dell'Energia

**Definizione**: la quantità totale di luce ri-emessa da una superficie (riflessa + scatter) non può mai essere superiore alla quantità di luce ricevuta.

$$\int_{\Omega} f_r(l, v) (n \cdot l) \, d\omega \leq 1$$

Dove:
- $f_r(l, v)$ è la BRDF
- $n$ è la normale della superficie
- $l$ è la direzione della luce
- $\Omega$ è l'emisfero superiore

**Implicazione pratica**: un materiale non può essere più luminoso della luce che lo illumina. In PBR, questo vincolo è gestito automaticamente dallo shader. Gli artisti non devono preoccuparsene esplicitamente, ma devono rispettare i range di albedo fisicamente plausibili (§2.8).

*Fonte: Allegorithmic PBR Guide Vol. 1, p. 7*

### 2.5 Effetto Fresnel e F0

L'**effetto Fresnel** descrive come la quantità di luce riflessa da una superficie dipende dall'angolo di incidenza.

**Osservazione fisica**: guardando una superficie d'acqua perpendicolarmente (angolo 0°), si può vedere il fondo. Guardandola ad angolo radente (~90°), diventa uno specchio quasi perfetto.

**Regola universale**: A 90° di incidenza radente (grazing angle), **tutte** le superfici lisce riflettono il 100% della luce, indipendentemente dal materiale.

$$F(\theta) \approx F_0 + (1 - F_0)(1 - \cos\theta)^5$$

Questa è l'**approssimazione di Schlick**, usata in quasi tutti i renderer real-time. Dove:
- $F_0$ è la riflettanza alla normale (0°)
- $\theta$ è l'angolo tra la normale e la direzione di vista
- Il termine $(1 - \cos\theta)^5$ modella la crescita rapida della riflessione agli angoli radenti

### 2.6 F0 — Fresnel Reflectance at 0 Degrees

L'F0 è il valore di riflettanza quando la luce colpisce la superficie perpendicolarmente.

**Relazione con IOR per dielettrici**:

$$F_0 = \left(\frac{n - 1}{n + 1}\right)^2$$

Dove $n$ è l'indice di rifrazione (IOR) del materiale.

**Esempio di calcolo**:
- Vetro comune: $n = 1.5$ → $F_0 = \left(\frac{0.5}{2.5}\right)^2 = 0.04$ (4%)
- Acqua: $n = 1.333$ → $F_0 \approx 0.02$ (2%)
- Diamante: $n = 2.417$ → $F_0 \approx 0.172$ (17.2%)

**Range fisici**:

| Categoria | F0 (lineare) | F0 (%) | sRGB equivalente |
|:----------|:------------|:-------|:-----------------|
| Dielettrici comuni | 0.017 – 0.067 | 1.7% – 6.7% | 40 – 75 sRGB |
| Gemme | 0.05 – 0.17 | 5% – 17% | 68 – 115 sRGB |
| Liquidi comuni | 0.02 – 0.04 | 2% – 4% | 51 – 61 sRGB |
| Metalli | 0.5 – 1.0 | 50% – 100% | 128 – 255 sRGB |

*Fonte: Allegorithmic PBR Guide Vol. 1, pp. 8-10; Vol. 2, pp. 15, 27; physicallybased.info*

> **Nota per metalli**: per i metalli, F0 è un numero **complesso** ($n + ik$) dove $k$ è il coefficiente di estinzione. I renderer PBR usano direttamente i valori RGB di F0 misurati, non l'IOR. La formula sopra vale solo per dielettrici trasparenti. *Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md; Valori_IOR doc*

### 2.7 IOR Complesso per i Metalli

Per i metalli, l'indice di rifrazione è un numero complesso:

$$\tilde{n} = n + ik$$

Dove:
- $n$ = parte reale (IOR convenzionale)
- $k$ = coefficiente di estinzione (absorption coefficient)

**Valori (n, k) per i principali metalli** *(Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md)*:

| Metallo | n | k | Note |
|:--------|:--|:--|:-----|
| Oro | 0.47 | 2.37 | $k$ controlla il colore giallo-arancio |
| Argento | 0.18 | 3.14 | Alta riflettanza, quasi neutro |
| Rame | 0.64 | 2.62 | $k$ produce il tono rosato |
| Ferro | 2.91 | 3.08 | Grigio neutro |
| Alluminio | 1.44 | 5.23 | Molto riflettente, tono freddo |

> **Nota critica**: I valori $n$ dei metalli riportati nelle liste IOR tradizionali (come la CGSociety IOR list) sono la parte reale $n$ dell'indice complesso, **non** il F0. Non sono direttamente utilizzabili come F0 in un renderer PBR senza considerare anche $k$. I renderer PBR usano i valori F0 RGB misurati spettrofotometricamente (vedi Sezione 3).

### 2.8 BRDF — Bidirectional Reflectance Distribution Function

La BRDF descrive le proprietà riflettive di una superficie. Per essere fisicamente plausibile, una BRDF deve essere:
1. **Energy conserving**: l'integrale su tutto l'emisfero non supera 1.0
2. **Reciproca** (Principio di reciprocità di Helmholtz): $f_r(l, v) = f_r(v, l)$

Il modello **Cook-Torrance** (con distribuzione GGX) è lo standard per PBR real-time:

$$f_r(l, v) = \frac{D(h) \cdot G(l, v) \cdot F(v, h)}{4(n \cdot l)(n \cdot v)}$$

Dove:
- $D(h)$ = **Distribution term** (GGX): distribuzione delle microfaccette
- $G(l, v)$ = **Geometry term**: auto-ombra e masking tra microfaccette
- $F(v, h)$ = **Fresnel term** (Schlick): variazione della riflessività con l'angolo
- $4(n \cdot l)(n \cdot v)$ = termine di normalizzazione

*Fonte: Allegorithmic PBR Guide Vol. 1, pp. 6-7; Compendio Tecnico PBR, Sezione 2*

La BRDF totale combina i contributi diffuso e speculare:

$$f_{total}(l, v) = f_{diffuse}(l, v) + f_{specular}(l, v)$$

Dove per i dielettrici:
$$f_{diffuse}(l, v) = \frac{albedo}{\pi} \cdot (1 - F(v, h))$$

Per i metalli, il termine diffuso è zero.

### 2.9 Distribuzione GGX (Trowbridge-Reitz)

La distribuzione GGX descrive la percentuale di microfaccette orientate nella direzione $h$:

$$D_{GGX}(h) = \frac{\alpha^2}{\pi \left((n \cdot h)^2(\alpha^2 - 1) + 1\right)^2}$$

Dove $\alpha = roughness^2$ (in alcune implementazioni $\alpha = roughness$).

**Vantaggio di GGX su Phong**: GGX ha un picco più corto nell'highlight ma una "coda lunga" nel falloff, producendo riflessi più realistici. Phong tende a dare un aspetto "plastico" e artificiale.

*Fonte: Allegorithmic PBR Guide Vol. 1, p. 6; Compendio Tecnico PBR*

### 2.10 Termine Geometrico di Smith (Shadowing-Masking)

$$G(l, v) = G_1(l) \cdot G_1(v)$$

$$G_1(x) = \frac{2(n \cdot x)}{(n \cdot x) + \sqrt{\alpha^2 + (1 - \alpha^2)(n \cdot x)^2}}$$

Questo termine riduce il contributo delle microfaccette bloccate dalla geometria circostante (shadowing dal lato della luce, masking dal lato dell'osservatore).

### 2.11 Fresnel di Schlick (Forma Espansa)

La formula completa include anche F90 per materiali con variazione cromatica ai bordi:

$$F(v, h) = F_0 + (F_{90} - F_0)(1 - v \cdot h)^5$$

Dove:
- $F_0$ = riflettanza alla normale (tabellata per materiale)
- $F_{90}$ = riflettanza agli angoli radenti (solitamente ~1.0 per dielettrici, specifica per metalli)

In OpenPBR e nei database come physicallybased.info, vengono forniti sia F0 che F82 (approssimazione a 82° per i metalli, anziché 90°, poiché a 90° la formula di Schlick non approssima bene i metalli).

### 2.12 Lambertian Diffuse Model

Il modello più semplice per la riflessione diffusa:

$$f_{Lambert}(l, v) = \frac{albedo}{\pi}$$

L'uscita è indipendente dalla direzione di vista (isotropa), costante su tutto l'emisfero. È una semplificazione: i modelli più accurati (Oren-Nayar) tengono conto della rugosità anche per il diffuso, ma Lambertian è adeguato per la maggior parte dei materiali PBR real-time.

### 2.13 Principio Energetico del Metalness Workflow

Nel workflow Metal/Roughness, la conservazione dell'energia è automaticamente garantita dal meccanismo metallic-mask:

$$\text{Se Metallic} = 0: \quad L_{out} = F_0 \cdot L_{specular} + (1 - F_0) \cdot albedo \cdot L_{diffuse}$$
$$\text{Se Metallic} = 1: \quad L_{out} = F_0 \cdot L_{specular} \quad (\text{no diffuse})$$

La maschera metallic controlla il bilanciamento diffuso/speculare, rendendo impossibile creare un materiale che violi la conservazione dell'energia.

Nel workflow Specular/Glossiness, la conservazione non è automatica: è responsabilità dell'artista non usare valori di diffuse e specular che sommati superino 1.0.

*Fonte: Allegorithmic PBR Guide Vol. 2, p. 4*

### 2.14 Anisotropia

Per superfici con micro-strutture direzionali (acciaio spazzolato, capelli, velluto), la distribuzione delle microfaccette non è simmetrica. La distribuzione anisotropica GGX è:

$$D_{aniso}(h) = \frac{1}{\pi \alpha_x \alpha_y} \cdot \frac{1}{\left(\frac{(h \cdot t)^2}{\alpha_x^2} + \frac{(h \cdot b)^2}{\alpha_y^2} + (h \cdot n)^2\right)^2}$$

Dove:
- $\alpha_x, \alpha_y$ = roughness lungo i due assi principali della superficie
- $t$ = tangent vector (direzione dei solchi/fibre)
- $b$ = bitangent vector

**Effetto visivo**: l'highlight speculare si allunga perpendicolarmente alla direzione dei solchi.

**Dati necessari**: mappa di Roughness + mappa di Anisotropy Amount + mappa di Rotation (per orientare i solchi).

*Fonte: Compendio Tecnico PBR, Sezione "Anisotropia"; DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md*

### 2.15 Subsurface Scattering (SSS)

La luce penetra in materiali parzialmente trasparenti (pelle, marmo, latte, cera), scattera internamente e riemerge in un punto diverso dall'entrata. Questo comportamento non è catturato dalla BRDF standard.

Il modello formale è la **BSSRDF** (Bidirectional Subsurface Scattering Reflectance Distribution Function):

$$S(x_i, l; x_o, v) = \frac{1}{\pi} F_t(x_i, l) \cdot R(|x_i - x_o|) \cdot F_t(x_o, v)$$

Dove $R(r)$ è il profilo di diffusione radiale che dipende dalla distanza tra punto di entrata $x_i$ e punto di uscita $x_o$.

**Parametri fisici misurati** *(Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md)*:

| Materiale | Scatter Distance | Anisotropy | Note |
|:----------|:----------------|:-----------|:-----|
| Pelle | 1–3 mm | 0.7–0.9 | Canale R viaggia più lontano |
| Marmo | 5–20 mm | 0.5–0.8 | SSS molto visibile in retroilluminazione |
| Latte | 10–50 mm | 0.8–0.95 | Partecipating medium |
| Cera | 2–10 mm | 0.6–0.8 | |
| Foglie | 0.5–2 mm | 0.6–0.8 | SSS visibile in controluce |

**Errore "waxy look"**: se i parametri SSS sono troppo elevati in relazione alla roughness, il materiale sembra cerato. Soluzione: ridurre lo scatter distance e aumentare leggermente la roughness.

### 2.16 Thin-Film Interference

Strati sottilissimi di materiale trasparente (bolle di sapone, anodizzazione titanio, perle madreperla) producono interferenza di colori dipendente dall'angolo di vista e dallo spessore del film.

$$\lambda_{peak} = \frac{2 \cdot n_{film} \cdot d \cdot \cos\theta}{m}$$

Dove:
- $d$ = spessore del film (in nm, tipicamente 100–1000 nm)
- $n_{film}$ = IOR del film
- $\theta$ = angolo di vista
- $m$ = ordine di interferenza

**Approssimazione real-time**: Fresnel + color ramp dipendente dall'angolo di vista (non è possibile simulare il fenomeno esatto senza shader dedicati).

*Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md*

### 2.17 Dispersione Cromatica (Diamante e Gemme)

Per materiali con alta dispersione (diamante), l'IOR varia con la lunghezza d'onda:

**Approssimazione per real-time** *(Fonte: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md)*:

| Canale | IOR (Diamante) |
|:-------|:--------------|
| R | ~2.40 |
| G | ~2.42 |
| B | ~2.45 |

Questa differenza produce l'effetto arcobaleno caratteristico del diamante. Nei renderer real-time è un'approssimazione, ma produce risultati visivamente credibili.

---

## [SEZIONE 3] DATABASE FISICO CONSOLIDATO

### 3.1 Struttura del Database

Questo database unifica i dati da:
- **physicallybased.info** (F0 misurati spettrofotometricamente)
- **CGSociety IOR List** (IOR di 200+ materiali)
- **SpectralDB** (misurazioni spettrofotometriche in sito)
- **Allegorithmic PBR Guide Vol. 2** (valori sRGB per workflow)
- **DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md** (range operativi)

**Legenda colonne database metalli**:
- `Base Color F0 (R,G,B)`: riflettanza alla normale in spazio lineare sRGB
- `Specular F0 (R,G,B)`: stesso dato in forma alternativa (physicallybased.info)
- `Specular F82 (R,G,B)`: riflettanza a 82° (approssimazione grazing angle)
- `Metallic`: sempre 1 per metalli puri
- `Densità`: kg/m³
- `Luminanza Rel.`: luminanza relativa percepita

**Legenda colonne database dielettrici**:
- `Base Color F0 (R,G,B)`: albedo in spazio lineare
- `Metallic`: sempre 0
- `Note SSS`: se applicabile

---

### 3.2 DATABASE METALLI — Valori Fisici Completi

*Fonte primaria: physicallybased.info — dati da misurazioni spettrofotometriche*
*Tutti i valori F0 in spazio lineare sRGB*

| Materiale | Base Color F0 (R,G,B) | Specular F0 (R,G,B) | Specular F82 (R,G,B) | Metallic | Densità kg/m³ | Lum. Rel. | Note |
|:----------|:----------------------|:---------------------|:---------------------|:---------|:-------------|:---------|:-----|
| **Alluminio** | 0.916, 0.923, 0.924 | 0.989, 0.989, 0.972 | 0.910, 0.936, 0.959 | 1 | 2700 | 0.922 | Tono freddo (B > R) |
| **All. Anodizzato Rosso** | 0.600, 0.000, 0.000 | 0.989, 0.989, 0.972 | 0.910, 0.936, 0.959 | 1 | 2700 | 0.128 | Colore nel Base Color |
| **Berillio** | 0.539, 0.533, 0.534 | 0.549, 0.503, 0.364 | 0.731, 0.738, 0.755 | 1 | 1850 | 0.534 | |
| **Ottone (Brass)** | 0.910, 0.778, 0.423 | 0.995, 0.974, 0.747 | 0.952, 0.979, 1.021 | 1 | 8600 | 0.780 | Lega Rame+Zinco |
| **Cesio** | 0.718, 0.554, 0.237 | 0.997, 1.002, 1.073 | 1.087, 1.180, 1.440 | 1 | 1886 | 0.566 | F82 > 1.0 fisicamente corretto |
| **Cromo** | 0.654, 0.685, 0.701 | 0.591, 0.675, 0.703 | 0.688, 0.728, 0.798 | 1 | 7200 | 0.680 | |
| **Cobalto** | 0.699, 0.704, 0.671 | 0.731, 0.775, 0.715 | 0.727, 0.772, 0.823 | 1 | 8900 | 0.701 | |
| **Rame (Copper)** | 0.932, 0.623, 0.522 | 0.999, 0.900, 0.744 | 0.982, 0.947, 0.945 | 1 | 8940 | 0.681 | Tono rosato (R >> B) |
| **Germanio** | 0.500, 0.517, 0.465 | 0.068, 0.179, 0.002 | 0.620, 0.653, 0.701 | 1 | 5327 | 0.510 | Semiconduttore |
| **Oro (Gold)** | 1.059, 0.773, 0.307 | 1.001, 0.985, 0.523 | 0.971, 1.018, 0.994 | 1 | 19320 | 0.800 | **F0 R > 1.0**: fisicamente corretto |
| **Iridio** | 0.745, 0.734, 0.704 | 0.818, 0.810, 0.727 | 0.759, 0.781, 0.810 | 1 | 22562 | 0.734 | |
| **Ferro (Iron)** | 0.530, 0.513, 0.494 | 0.612, 0.541, 0.422 | 0.765, 0.767, 0.802 | 1 | 7870 | 0.515 | |
| **Piombo (Lead)** | 0.626, 0.640, 0.693 | 0.717, 0.717, 0.696 | 0.758, 0.773, 0.799 | 1 | 11340 | 0.641 | |
| **Litio** | 0.916, 0.890, 0.807 | 0.998, 0.995, 0.975 | 0.985, 0.998, 1.027 | 1 | 535 | 0.890 | |
| **Magnesio** | 0.956, 0.953, 0.950 | 0.998, 0.996, 0.983 | 0.954, 0.964, 0.977 | 1 | 1737 | 0.953 | |
| **Manganese** | 0.606, 0.592, 0.573 | 0.757, 0.761, 0.715 | 0.796, 0.834, 0.889 | 1 | 7476 | 0.594 | |
| **Mercurio** | 0.781, 0.780, 0.778 | 0.901, 0.910, 0.890 | 0.813, 0.852, 0.902 | 1 | 13546 | 0.780 | |
| **Molibdeno** | 0.589, 0.612, 0.594 | 0.495, 0.505, 0.383 | 0.683, 0.696, 0.726 | 1 | 10223 | 0.606 | |
| **Nichel (Nickel)** | 0.697, 0.641, 0.563 | 0.855, 0.805, 0.675 | 0.815, 0.834, 0.871 | 1 | 8900 | 0.647 | |
| **Palladio** | 0.734, 0.704, 0.662 | 0.874, 0.854, 0.779 | 0.811, 0.836, 0.872 | 1 | 12007 | 0.707 | |
| **Platino (Platinum)** | 0.765, 0.730, 0.676 | 0.873, 0.850, 0.747 | 0.793, 0.815, 0.840 | 1 | 21450 | 0.734 | |
| **Potassio** | 0.983, 0.956, 0.906 | 1.000, 1.000, 0.994 | 1.002, 1.011, 1.032 | 1 | 859 | 0.958 | |
| **Rubidio** | 0.919, 0.859, 0.747 | 1.000, 0.999, 0.998 | 1.016, 1.042, 1.105 | 1 | 1534 | 0.864 | |
| **Silicio** | 0.345, 0.369, 0.426 | 0.081, 0.000, 0.004 | 0.720, 0.701, 0.663 | 1 | 2330 | 0.368 | Semiconduttore; B > R |
| **Argento (Silver)** | 0.991, 0.985, 0.974 | 1.000, 1.000, 0.991 | 0.994, 0.995, 0.998 | 1 | 10500 | 0.985 | |
| **Sodio** | 0.977, 0.962, 0.936 | 1.000, 1.000, 0.991 | 0.998, 1.002, 1.011 | 1 | 969 | 0.963 | |
| **Acciaio Inox** | 0.669, 0.639, 0.598 | 0.804, 0.791, 0.714 | 0.789, 0.823, 0.870 | 1 | 7500 | 0.642 | |
| **Titanio** | 0.441, 0.400, 0.361 | 0.670, 0.641, 0.520 | 0.865, 0.906, 0.946 | 1 | 4540 | 0.406 | |
| **Titanio Anodizzato** | 0.441, 0.400, 0.361 | 0.670, 0.641, 0.520 | 0.865, 0.906, 0.946 | 1 | 4540 | 0.406 | Thin-film color su strato anodizzato |
| **Tungsteno** | 0.537, 0.536, 0.519 | 0.450, 0.409, 0.193 | 0.695, 0.704, 0.714 | 1 | 19300 | 0.535 | |
| **Vanadio** | 0.534, 0.526, 0.546 | 0.474, 0.426, 0.175 | 0.705, 0.715, 0.695 | 1 | 6100 | 0.529 | |
| **Zinco** | 0.808, 0.844, 0.865 | 0.854, 0.922, 0.923 | 0.762, 0.833, 0.896 | 1 | 7000 | 0.838 | |

**Valori sRGB di riferimento per workflow artistico** *(Fonte: Allegorithmic PBR Guide Vol. 2, Fig. 48)*:

| Metallo | sRGB Approx. |
|:--------|:------------|
| Oro | (255, 226, 155) |
| Argento | (252, 250, 245) |
| Alluminio | (245, 246, 246) |
| Ferro | (196, 199, 199) |
| Rame | (250, 208, 192) |
| Titanio | (193, 186, 177) |
| Nichel | (211, 203, 190) |
| Cobalto | (211, 210, 207) |
| Platino | (213, 208, 200) |

> **Nota critica**: i valori F0 sopra 1.0 (es. Oro R: 1.059, Cesio B: 1.440) sono fisicamente corretti in spazio lineare. I metalli possono avere riflettanze superiori a 1.0 in certi canali spettrali. I renderer HDR li gestiscono correttamente; nei renderer che applicano clamp a 1.0, si introduce un errore di colore. *Fonte: physicallybased.info; nota critica PBR_MKB_Part1*

---

### 3.3 DATABASE NON-METALLI (DIELETTRICI) — Valori Fisici Completi

*Fonte primaria: physicallybased.info — dati spettrofotometrici*
*Tutti i valori in spazio lineare. Metallic = 0 per tutti.*

| Materiale | Base Color F0 (R,G,B) lineare | Lum. Rel. | Densità kg/m³ | SSS | Note |
|:----------|:------------------------------|:---------|:-------------|:----|:-----|
| **Asfalto fresco** | 0.043, 0.041, 0.040 | 0.042 | — | No | |
| **Banana** | 0.634, 0.532, 0.111 | 0.523 | — | No | |
| **Lavagna (Blackboard)** | 0.039, 0.039, 0.039 | 0.039 | — | No | |
| **Osso (Bone)** | 0.793, 0.793, 0.664 | 0.784 | 1000 | No | |
| **Mattone (Brick)** | 0.262, 0.095, 0.061 | 0.128 | 500–2400 | No | Densità molto variabile per tipo |
| **Cartone (Cardboard)** | 0.351, 0.208, 0.110 | 0.231 | 700 | No | |
| **Carota** | 0.713, 0.170, 0.026 | 0.275 | — | No | |
| **Carbone (Charcoal)** | 0.020, 0.020, 0.020 | 0.020 | 200 | No | Valore minimo per materiale comune |
| **Cioccolato** | 0.162, 0.091, 0.060 | 0.104 | 1229 | No | |
| **Cemento (Concrete)** | 0.510, 0.510, 0.510 | 0.510 | 2400 | No | Quasi grigio neutro |
| **Guscio uovo (marrone)** | 0.493, 0.248, 0.123 | 0.291 | — | No | |
| **Guscio uovo (bianco)** | 0.610, 0.624, 0.631 | 0.622 | — | No | |
| **Erba (Grass)** | 0.105, 0.133, 0.041 | 0.120 | — | No | |
| **Gray Card 18%** | 0.180, 0.180, 0.180 | 0.180 | — | No | Standard 18% reflectance |
| **Miele cristallizzato** | 0.449, 0.319, 0.011 | 0.324 | 1380 | No | |
| **Limone** | 0.617, 0.366, 0.045 | 0.396 | — | No | |
| **Marmo** | 0.830, 0.791, 0.753 | 0.797 | 2700 | **Sì** | SSS visibile |
| **Latte (Milk)** | 0.815, 0.813, 0.682 | 0.804 | 1026 | **Sì** | |
| **MIT Black** | 0.000, 0.000, 0.000 | 0.000 | — | No | Nanotubi carbonio — minimo assoluto |
| **Musou Black** | 0.006, 0.006, 0.006 | 0.006 | — | No | Vernice più scura disponibile |
| **Carta da ufficio** | 0.794, 0.834, 0.884 | 0.829 | 800 | No | **Canale B anomalo** (fluorescenza UV) |
| **Perla** | 0.800, 0.750, 0.700 | 0.757 | 2700 | No | Thin-film nacre |
| **Porcellana** | 0.745, 0.745, 0.723 | 0.743 | 2000 | No | |
| **Sabbia (Sand)** | 0.440, 0.386, 0.231 | 0.386 | 1440 | No | |
| **Pelle I (chiara)** | 0.847, 0.638, 0.552 | 0.676 | 1020 | **Sì** | |
| **Pelle II** | 0.799, 0.485, 0.347 | 0.542 | 1020 | **Sì** | |
| **Pelle III** | 0.623, 0.433, 0.343 | 0.467 | 1020 | **Sì** | |
| **Pelle IV** | 0.436, 0.227, 0.131 | 0.265 | 1020 | **Sì** | |
| **Pelle V** | 0.283, 0.148, 0.079 | 0.172 | 1020 | **Sì** | |
| **Pelle VI (scura)** | 0.090, 0.050, 0.020 | 0.056 | 1020 | **Sì** | |
| **Neve (Snow)** | 0.850, 0.850, 0.850 | 0.850 | 90 | No | |
| **Spectralon** | 0.990, 0.990, 0.990 | 0.990 | — | No | Massima riflettanza diffusa misurabile |
| **Terracotta** | 0.555, 0.212, 0.110 | 0.278 | 1800 | No | |
| **Pneumatico (Tire)** | 0.023, 0.023, 0.023 | 0.023 | — | No | |
| **Dentifricio** | 0.932, 0.937, 0.929 | 0.935 | 1300 | No | |
| **Carta igienica** | 0.830, 0.835, 0.784 | 0.830 | 20 | No | |
| **Lavagna bianca** | 0.869, 0.867, 0.771 | 0.860 | — | No | |

> **Nota carta da ufficio**: il canale B (0.884) è superiore a R (0.794) — comportamento anomalo dovuto agli **optical brighteners** (agenti fluorescenti UV) che emettono nel blu sotto luce ultravioletta. Non è un semplice albedo; richiede un termine emissive supplementare nel canale blu per simulazione accurata. *Fonte: PBR_MKB_Part1; DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md*

---

### 3.4 RANGE DI VALIDAZIONE ALBEDO — Regole Operative

*Sintesi da: Allegorithmic PBR Guide Vol. 2; physicallybased.info; DOMANDE_PER_LA_PARTE_2*

#### Range sRGB 8-bit per Dielettrici

| Categoria | Range Min (sRGB) | Range Max (sRGB) | Note |
|:----------|:----------------|:----------------|:-----|
| **Dielettrici — range operativo** | 30 (tolerant) / 50 (strict) | 240 | McDermott: "dark values should not go below 30–50" |
| **Dielettrici scuri** | 30 | 120 | Carbone, asfalto, terra bagnata |
| **Dielettrici medi** | 80 | 180 | La maggioranza dei materiali naturali |
| **Dielettrici chiari** | 120 | 240 | Sabbia, cemento, legno chiaro |
| **Neve, carta bianca** | 200 | 250 | Range estremo fisicamente giustificato |
| **Carbone, MIT Black** | 0 | 30 | Eccezione documentata: materiali ultra-assorbenti |

#### Range sRGB 8-bit per Metalli

| Categoria | Range Min (sRGB) | Range Max (sRGB) | Note |
|:----------|:----------------|:----------------|:-----|
| **Metalli puri (grezzo, lucidato)** | 180 | 255 | 70–100% speculare |
| **Metallo arrugginito** | 52 | 52 | Trattato come dielettrico: sRGB ~(52,52,52) per ferro arrugginito |
| **Metallo con sporco/verniciato** | (dipende dal materiale sopra) | — | Metallic degradato, trattare come dielettrico parziale |

*Fonte: Allegorithmic PBR Guide Vol. 2, p. 6, 8, 27; DOMANDE_PER_LA_PARTE_2*

> **Conflitto di dati documentato**: La guida Allegorithmic (Vol. 2) cita il range sRGB per dielettrici come **30–240** (tolerant) e **50–240** (strict). L'appendice integrativa cita lo stesso range come **30–240** senza distinzione di "tolerant/strict". Si adotta il riferimento primario Allegorithmic che include entrambi i threshold.

---

### 3.5 PROFILI FISICI PBR — Materiali Standard per Validazione

*Fonte: PBR_MKB_Part1 §8.2; DVAMOCLES Spec v3.1-FINAL §8.2*

Questi profili sono usati dal sistema di validazione DVAMOCLES (Material Health Check) per il sanity check adattivo.

#### Mattone (Brick)
```
albedo_sRGB:  120–160
roughness:    0.7–0.9
metallic:     0
specular_F0:  0.04
micro_var:    alta
note:         Albedo varia con tipo (rosso, bianco, nero)
```

#### Cemento / Malta (Cement/Mortar)
```
albedo_sRGB:  160–200
roughness:    0.8–0.95
metallic:     0
specular_F0:  0.04
cavity:       pronunciata
```

#### Legno Grezzo Non Levigato (Wood Raw)
```
albedo_sRGB:  80–180 (dipende dalla specie)
roughness:    0.6–0.85
metallic:     0
specular_F0:  0.04–0.05  ← ECCEZIONE VALIDATA: unico dielettrico con F0 > 0.04 in v1.0
note:         Pino 120–160, Quercia 100–140, Ebano 30–60, Frassino 140–180
```
*Fonte per albedo legno per specie: DOMANDE_PER_LA_PARTE_2_risposte_brevementi.md*

#### Ferro / Acciaio (Iron/Steel)
```
albedo_reflect_sRGB: ~180–210 (valori da database fisico: 0.530–0.669 lineare)
roughness:           0.2–0.6 (dipende dall'usura)
metallic:            1
note:                Ferro arrugginito → metallic 0, trattare come dielettrico
```

#### Rame (Copper)
```
albedo_rgb_sRGB: ~(250, 208, 192) — oppure ~(190, 120, 60) in scala diversa
roughness:       0.3–0.6
metallic:        1
```
> **Conflitto documentato**: PBR_MKB_Part1 cita `albedo_rgb: ~190, 120, 60` come valori sRGB. Il database physicallybased.info fornisce i valori lineari `0.932, 0.623, 0.522`, che convertiti corrispondono a ~`(250, 208, 192)` sRGB. Entrambi i riferimenti descrivono lo stesso materiale; la discrepanza è di conversione gamma. Si adottano i valori physicallybased.info come fonte primaria per la linearità dei dati.

#### Oro (Gold)
```
albedo_rgb_linear: 1.059, 0.773, 0.307 (nota: R > 1.0 fisicamente corretto)
albedo_rgb_sRGB:   ~(255, 226, 155)
roughness:         0.2–0.5
metallic:          1
```

---

### 3.6 DATABASE IOR — Indici di Rifrazione Completo

*Fonte primaria: CGSociety IOR List (http://forums.cgsociety.org/t/a-complete-ior-list/1070401)*
*Per la relazione IOR → F0 per dielettrici: $F_0 = \left(\frac{n-1}{n+1}\right)^2$*

> **Avvertenza metalli**: i valori IOR dei metalli in questa lista sono la parte reale $n$ dell'indice complesso. Non usare la formula F0 = ((n-1)/(n+1))² per i metalli. Usare i valori F0 RGB del database physicallybased.info (Sezione 3.2).

#### Aria e Vuoto
| Materiale | IOR | F0 calcolato |
|:----------|:----|:-------------|
| Vuoto | 1.000000 | 0.000 |
| Aria (20°C, 1 atm) | 1.000293 | ~0.000 |

#### Liquidi

| Materiale | IOR | F0 calcolato | Note |
|:----------|:----|:-------------|:-----|
| Acqua (0°C) | 1.33346 | 0.020 | |
| Acqua (20°C) | 1.33283 | 0.020 | Standard utilizzato |
| Acqua (100°C) | 1.31766 | 0.018 | |
| Ghiaccio | 1.309 | 0.018 | |
| Alcool etilico | 1.36 | 0.022 | |
| Acetone | 1.36 | 0.022 | |
| Birra | 1.345 | 0.021 | |
| Glicerina | 1.473 | 0.037 | |
| Miele (13% H₂O) | 1.504 | 0.042 | |
| Miele (17% H₂O) | 1.494 | 0.040 | |
| Miele (21% H₂O) | 1.484 | 0.039 | |
| Latte | 1.35 | 0.021 | |
| Olio vegetale (50°C) | 1.47 | 0.035 | |
| Olio safflower | 1.466 | 0.034 | |

#### Vetri e Cristalli

| Materiale | IOR | F0 calcolato |
|:----------|:----|:-------------|
| Vetro Crown (comune) | 1.52 | 0.043 |
| Vetro Flint leggero | 1.58 | 0.051 |
| Vetro Flint pesante | 1.66 | 0.063 |
| Quarzo fuso | 1.45843 | 0.035 |
| Plexiglas/PMMA | 1.50 | 0.040 |
| Vetro borosilicato | 1.50 | 0.040 |
| Vetro borosilicato standard | 1.517 | 0.043 | Valore "standard finestra" |
| Agata | 1.544 | 0.046 | |
| Ametista | 1.544 | 0.046 | |
| Acquamarina | 1.577 | 0.051 | |
| Aragonite | 1.530 | 0.044 | |
| Azzurrite | 1.730 | 0.072 | |
| Calcite | 1.486 | 0.038 | |
| Chalcedony | 1.530 | 0.044 | |
| Gesso (Chalk) | 1.510 | 0.041 | |
| Corindone | 1.766 | 0.075 | |
| **Diamante** | **2.417** | **0.172** | Massimo tra gemme comuni |
| Smeraldo | 1.576 | 0.051 | |
| Fluorite | 1.434 | 0.030 | |
| Giadeite | 1.665 | 0.063 | |
| Lapislazzuli | 1.610 | 0.055 | |
| Malachite | 1.655 | 0.062 | |
| Ossidiana | 1.489 | 0.038 | |
| Opale | 1.450 | 0.032 | |
| Perla | 1.530 | 0.044 | |
| Quarzo | 1.544 | 0.046 | |
| **Rubino** | **1.760** | **0.072** | |
| **Zaffiro** | **1.760** | **0.072** | |
| Roccia salina | 1.544 | 0.046 | |
| Topazio | 1.620 | 0.056 | |
| Tormalina | 1.624 | 0.056 | |
| **Zirconia cubica** | **2.170** | **0.132** | |
| Zircone alto | 1.960 | 0.096 | |
| Zircone basso | 1.800 | 0.081 | |

#### Plastiche e Polimeri

| Materiale | IOR | F0 calcolato |
|:----------|:----|:-------------|
| Nylon | 1.53 | 0.044 |
| Plastica generica | 1.460 | 0.034 |
| Policarbonato | 1.586 | 0.052 |
| PMMA / Acrilico | 1.492 | 0.039 |

#### Minerali e Rocce

| Materiale | IOR | F0 calcolato |
|:----------|:----|:-------------|
| Asfalto | 1.635 | 0.059 |
| Ambra | 1.546 | 0.046 |
| Barite | 1.636 | 0.059 |
| Corallo | 1.486 | 0.038 |
| Anatase | 2.490 | 0.185 | TiO₂ |
| Solfuro | 1.960 | 0.096 | |

#### Metalli — IOR parte reale $n$ (NON usare come F0)

> Questi valori provengono dalla CGSociety IOR List e rappresentano solo la parte reale $n$ dell'indice complesso. Per i F0 fisicamente corretti dei metalli, usare il database §3.2.

| Metallo | IOR $n$ (CGSociety) | F0 reale (physicallybased.info) | Discrepanza |
|:--------|:--------------------|:-------------------------------|:------------|
| Alluminio | 1.44 | 0.922 | ⚠️ Non usare CGS per F0 |
| Rame | 1.10 | 0.681 | ⚠️ Non usare CGS per F0 |
| Oro | 0.47 | 0.800 | ⚠️ IOR < 1.0: normale per metalli |
| Argento | 0.18 | 0.985 | ⚠️ IOR << 1.0: normale per metalli |
| Ferro | 1.51 | 0.515 | ⚠️ Non usare CGS per F0 |
| Cromo | 2.97 | 0.680 | ⚠️ Non usare CGS per F0 |
| Platino | 2.33 | 0.734 | ⚠️ Non usare CGS per F0 |
| Acciaio | 2.50 | ~0.642 (acciaio inox) | ⚠️ Non usare CGS per F0 |
| Titanio | 2.16 | 0.406 | ⚠️ Non usare CGS per F0 |

> **Spiegazione della discrepanza**: I metalli hanno IOR complesso $\tilde{n} = n + ik$. L'indice $n$ nella lista CGS può essere inferiore a 1.0 (Oro: 0.47, Argento: 0.18) — questo è fisicamente corretto. La formula $F_0 = ((n-1)/(n+1))^2$ vale solo per dielettrici trasparenti. Per i metalli è necessario usare la formula di Fresnel con numeri complessi, il cui risultato è già tabulato in physicallybased.info.

---

### 3.7 DATI SPETTRALI — SpectralDB

*Fonte: SpectralDB (Jakubiec, J.A.) — misurazioni spettrofotometriche in sito su materiali architettonici*
*Metodologia: spettrofotometro portatile, campioni in sito, SCI (Specular Component Included) e SCE (Specular Component Excluded)*

#### Struttura dei dati SpectralDB

Ogni entry contiene:
- **RGB (8-bit)**: colore approssimato in sRGB
- **L\*a\*b\*** (CIELab): rappresentazione perceptually uniform
- **SCI**: riflettanza spettrale totale (diffusa + speculare), 360–740nm, step 10nm
- **SCE**: riflettanza spettrale solo diffusa (esclude componente speculare)
- **Specularity**: indice relativo di brillantezza superficiale (0.01–2.05 nel campione)
- **Roughness**: stima rugosità (0.2–0.3 nel campione)

#### SCI vs SCE — Significato per PBR

| Misura | Cosa rappresenta | Uso PBR |
|:-------|:----------------|:--------|
| **SCI** | Riflettanza totale (diffusa + speculare) | Riferimento per conservazione energetica |
| **SCE** | Solo componente diffusa | **Fonte più corretta per Base Color/Albedo** |

> Il valore SCE è più appropriato come riferimento per il canale Base Color in workflow Metal/Roughness, poiché esclude il picco speculare che viene gestito separatamente da Roughness + F0.

#### Campioni SpectralDB Rappresentativi

| ID | Materiale | Tipo | RGB 8-bit (SCI) | Specularity | Roughness |
|:---|:----------|:-----|:----------------|:------------|:----------|
| 1 | Pareti bianche | Muro | (138, 135, 120) | 0.36 | 0.2 |
| 2 | Piastrelle grigio scuro | Pavimento | (33, 31, 28) | **2.05** | 0.2 |
| 1288 | Intonaco bianco CH | Muro | (146, 144, 135) | 0.22 | 0.3 |
| 1289 | Intonaco bianco NL | Muro | (135, 132, 117) | 0.01 | 0.3 |
| 1290 | Parete plastica bianca NL | Muro | (143, 142, 139) | 0.09 | 0.3 |

> **Nota sulla Specularity**: Il valore 2.05 per le piastrelle grigio scuro indica una superficie molto lucida. Questo **non** è equivalente al F0 PBR — è un indice relativo strumentale. Superfici ceramiche lucidate mostrano valori superiori a 1.0 in questa scala.

#### SpectralDB e Validazione Albedo

L'analisi del dataset SpectralDB (1294 entries) conferma la distribuzione fisica degli albedo:
- Materiali architettonici comuni: L* tra 30 e 90
- Superfici nere (ardesia, asfalto): L* 10–25
- Superfici bianche (intonaco, carta): L* 80–95
- Range operativo per la gran parte dei materiali costruttivi: sRGB ~60–220

---

### 3.8 SPECULAR F0 IN WORKFLOW SPECULAR/GLOSSINESS

Nel workflow Specular/Glossiness, il canale Specular contiene esplicitamente i valori F0.

**Per dielettrici** (in sRGB):

| Range sRGB | F0 lineare | Categoria |
|:-----------|:-----------|:----------|
| 40–75 sRGB | 0.017–0.067 | Comuni dielettrici |
| 55–63 sRGB | 0.022–0.040 | Plastica, legno, pietra, mattone, cemento, tessuto |
| 40–44 sRGB | 0.017–0.020 | Acqua, ghiaccio, liquidi comuni |
| 56–61 sRGB | 0.023–0.040 | Plastica standard |
| 56–61 sRGB | 0.023–0.040 | Vetro finestra |
| 68–90 sRGB | 0.050–0.080 | Gemme comuni |
| 0 sRGB | 0.000 | Aria (usata come floor del range) |

> **Regola di fallback**: se non si conosce l'IOR di un dielettrico specifico, usare 4% (0.04 lineare, ~61 sRGB). Questo è il valore corretto per plastica, vetro comune, legno, cemento e la maggioranza dei materiali non-metallici.
>
> *Fonte: Allegorithmic PBR Guide Vol. 2, pp. 14-15*

**Per metalli** (in sRGB): usare i valori tabulati in §3.2 convertiti da lineare a sRGB (range 180–255 sRGB).

---

### 3.9 CONFRONTO WORKFLOW: DOVE VANNO I DATI

| Dato | Metal/Roughness | Specular/Glossiness |
|:-----|:----------------|:--------------------|
| Albedo dielettrico | Base Color (RGB) | Diffuse (RGB) |
| F0 dielettrico | Shader automatico (0.04) | **Specular (RGB)** |
| Reflectance metallo | Base Color (RGB) | Specular (RGB) |
| Diffuse metallo | Shader automatico (nero) | **Diffuse (nero puro)** |
| Roughness | Roughness map (lineare) | Glossiness map (1-Roughness, lineare) |
| Metal mask | Metallic map (0 o 1) | Non presente (implicito nel Specular/Diffuse) |

*Fonte: Allegorithmic PBR Guide Vol. 2, pp. 2-5*

---

### 3.10 SPECULAR LEVEL — Override F0 nel Workflow Metal/Roughness

Alcune implementazioni del workflow Metal/Roughness (Unreal Engine 4/5, Substance) includono un canale opzionale **Specular Level** (anche detto `specularLevel`) che permette di sovrascrivere il valore F0 fisso di 0.04 per i dielettrici.

In Substance Designer, questo output mappa il range:
$$SpecularLevel_{input} \in [0.0, 0.08] \rightarrow F_0 \in [0\%, 8\%]$$

Il valore 0.5 sul canale (che corrisponde al midpoint 0.04) è il default per la maggior parte dei materiali.

*Fonte: Allegorithmic PBR Guide Vol. 2, p. 5*

---

## FINE PARTE A

> **Prossima sezione (Parte B)**: Logica Procedurale e Pipeline — Texel Density, Layering System, LOD Strategy, Normal Map workflow, AO creation, Height/Displacement, Car Paint multi-layer, workflow fotogrammetria, LOD degradation, Sanity Check procedurale.
>
> Digitare **"continua"** per procedere con la Parte B.
