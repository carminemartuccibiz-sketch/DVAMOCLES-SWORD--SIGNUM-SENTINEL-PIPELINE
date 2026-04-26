# PBR MASTER KNOWLEDGE BASE — PARTE 1: FONDAMENTI TEORICI
## Documento di Conoscenza Teorica Pura — Computer Grafica & Asset 3D
**Versione: 1.0 | Data: 2026-04-11 | Classificazione: Riferimento Tecnico Permanente**
**Fonti integrate: Physically Based Database, SpectralDB, File Type Research, IOR List**

> **Nota metodologica**: Questo documento estrae esclusivamente principi fisici, regole di settore e dati misurati. Non contiene istruzioni operative relative ad alcun software. I dati discordanti tra fonti sono entrambi riportati con indicazione della fonte, senza risoluzione arbitraria.

---

## INDICE

1. [PRINCIPI FONDAMENTALI DEL PBR](#1)
2. [CLASSIFICAZIONE DEI MATERIALI](#2)
3. [DATABASE DEI VALORI FISICI — METALLI](#3)
4. [DATABASE DEI VALORI FISICI — NON-METALLI](#4)
5. [INDICE DI RIFRAZIONE (IOR) — RIFERIMENTO COMPLETO](#5)
6. [DATI SPETTRALI — SpectralDB](#6)
7. [GESTIONE DEL COLORE E SPAZI COLORE](#7)
8. [TIPOLOGIE DI MAPPE TEXTURE E LORO RUOLO PBR](#8)
9. [FORMATI FILE — CLASSIFICAZIONE TECNICA](#9)
10. [COMPRESSIONE GPU — STANDARD BCn](#10)
11. [REGOLE DI VALIDAZIONE PBR](#11)
12. [DOMANDE PER LA PARTE 2](#12)

---

## 1. PRINCIPI FONDAMENTALI DEL PBR {#1}

### 1.1 Definizione di Physically Based Rendering

Il PBR (Physically Based Rendering) è un approccio al rendering in tempo reale che simula il comportamento fisico della luce a contatto con i materiali. Si basa su tre pilastri fisici fondamentali:

**Conservazione dell'energia**: la luce riflessa non può essere superiore alla luce incidente. Un materiale non può riflettere più del 100% della luce che lo colpisce. Questa legge fisica impone che albedo troppo alta (valori vicini a 1.0) o troppo bassa (valori vicini a 0.0) siano fisicamente non plausibili nella maggior parte dei materiali reali.

**Riflessione di Fresnel**: ogni superficie riflette più luce quando vista ad angoli rasanti (angoli molto obliqui rispetto alla normale della superficie) e meno luce quando vista frontalmente (angolo 0°). Questo fenomeno è universale e vale per tutti i materiali, sia metallici che dielettrici. Il valore F0 descrive la riflessività al normale (0°), mentre F82 o F90 descrivono la riflessività agli angoli rasanti.

**Microfacets**: le superfici reali non sono perfettamente piatte a livello microscopico. Il parametro Roughness descrive la distribuzione statistica delle normali delle microfaccette. Una Roughness pari a 0.0 corrisponde a una superficie perfettamente speculare (tipo specchio). Una Roughness pari a 1.0 corrisponde a una superficie completamente diffusa.

### 1.2 Workflow Metallic-Roughness vs Specular-Glossiness

Esistono due workflow principali per la definizione dei materiali PBR. I dati in questo documento seguono il workflow **Metallic-Roughness** (standard UE5/Unity moderno).

**Workflow Metallic-Roughness** (standard moderno):
- Albedo / Base Color: colore diffuso (per i dielettrici) o colore di riflessione (per i metalli)
- Metallic: canale binario — 0 per dielettrici, 1 per metalli puri
- Roughness: distribuzione delle microfaccette (0 = specchio, 1 = completamente opaco)

**Workflow Specular-Glossiness** (legacy, ancora in uso in alcuni tool):
- Diffuse: colore diffuso
- Specular: colore e intensità della riflessione speculare
- Glossiness: inverso della Roughness (1 = specchio, 0 = completamente opaco)

⚠️ **Nota di conversione**: Glossiness = 1 - Roughness. Questa conversione è matematicamente esatta ma può introdurre errori di gamma se non gestita correttamente.

### 1.3 Il Modello di Cook-Torrance

Il modello BRDF (Bidirectional Reflectance Distribution Function) più diffuso nei renderer moderni è il Cook-Torrance, che combina:
- Termine diffusivo (Lambertiano): luce diffusa in modo uniforme
- Termine speculare (microfacets): luce riflessa secondo la distribuzione delle microfaccette
- Fresnel: variazione della riflessività con l'angolo di incidenza
- Distribuzione GGX: distribuzione delle normali delle microfaccette (più fisicamente accurata di Beckmann)

---

## 2. CLASSIFICAZIONE DEI MATERIALI {#2}

### 2.1 Dielettrici (Non-Metalli)

I dielettrici sono materiali non conduttori: plastica, legno, ceramica, pietra, tessuto, pelle, ecc.

**Caratteristiche fisiche fondamentali**:
- Il canale **Metallic = 0** (o molto vicino a 0)
- Il valore **F0** (riflettanza alla normale) è quasi sempre compreso tra **0.02 e 0.05** per i materiali comuni
- **La regola universale del F0 = 0.04**: la stragrande maggioranza dei dielettrici ha un valore di riflettanza speculare alla normale di circa 4% (0.04 in spazio lineare). Questo valore corrisponde a un IOR di circa 1.5, che è tipico del vetro comune, della plastica e di molti minerali
- Il colore dell'albedo porta l'informazione cromatica principale del materiale
- L'albedo dei dielettrici ha range fisicamente plausibili: il range sRGB validato è generalmente **30–240 sRGB** (circa 0.12–0.94 in lineare)
- Valori di albedo al di sotto di 30 sRGB sono fisicamente plausibili solo per materiali molto scuri (carbone, asfalto, pneumatici); valori al di sopra di 240 sRGB sono fisicamente plausibili solo per materiali molto bianchi come neve fresca o Spectralon

### 2.2 Metalli (Conduttori)

I metalli sono materiali conduttori: oro, argento, rame, ferro, alluminio, ecc.

**Caratteristiche fisiche fondamentali**:
- Il canale **Metallic = 1** (o molto vicino a 1)
- I metalli **non hanno colore diffuso**: tutta la luce che non viene riflessa viene assorbita
- La riflessività speculare dei metalli è alta e **ha un colore** (ad esempio l'oro è giallo-arancio, il rame è rosso-arancio)
- Il valore F0 per i metalli è tipicamente compreso tra **0.5 e 0.99** in spazio lineare
- I metalli ossidati o contaminati possono avere valori Metallic intermedi nella transizione tra metallo puro e ossido (dielettrico)
- ⚠️ **Errore comune**: assegnare albedo colorata a un metallo puro nel workflow Metallic-Roughness. Il colore di un metallo puro va nel canale Base Color/Albedo come riflessività speculare, non come colore diffuso separato

### 2.3 Materiali Speciali e Casi Limite

**Anodizzazione** (Alluminio, Titanio): la processo di anodizzazione crea un layer di ossido trasparente sulla superficie metallica. Questo layer agisce come un film thin-film e può produrre colori da interferenza. Nel database:
- Alluminio Anodizzato Rosso: Base Color F0 = 0.600, 0.000, 0.000 — Metallic = 1 — il colore è nell'albedo ma il comportamento speculare resta metallico
- Titanio Anodizzato: il Titanio può produrre colori vivaci dall'anodizzazione (a differenza dell'Alluminio che usa pigmenti aggiuntivi)

**Thin-film interference** (Bolle di sapone, Perle Nacre): produce colori iridescenti che cambiano con l'angolo di visione. Il modello Metallic-Roughness standard non cattura questo fenomeno senza shader personalizzati.

**Materiali SSS** (Subsurface Scattering): pelle, marmo, cera, latte, gelatina. La luce penetra nella superficie e viene diffusa internamente prima di uscire. Questo comportamento non è catturato dal solo canale Albedo ma richiede parametri aggiuntivi.

---

## 3. DATABASE DEI VALORI FISICI — METALLI {#3}

*Fonte: physicallybased.info — Dati derivati da misurazioni spettrofotometriche e database di indici di rifrazione*
*Tutti i valori Base Color (F0) e Specular Color sono in spazio lineare sRGB.*
*F0 = riflettanza alla normale (0°) | F82/F90 = riflettanza agli angoli rasanti | Relative Luminance = luminanza relativa percepita*

| Materiale | Base Color F0 (R,G,B) | Metallic | Specular F0 (R,G,B) | Specular F82 (R,G,B) | Densità kg/m³ | Luminanza Rel. |
|:----------|:----------------------|:---------|:--------------------|:---------------------|:--------------|:---------------|
| Alluminio | 0.916, 0.923, 0.924 | 1 | 0.989, 0.989, 0.972 | 0.910, 0.936, 0.959 | 2700 | 0.922 |
| Alluminio Anodizzato Rosso | 0.600, 0.000, 0.000 | 1 | 0.989, 0.989, 0.972 | 0.910, 0.936, 0.959 | 2700 | 0.128 |
| Berillio | 0.539, 0.533, 0.534 | 1 | 0.549, 0.503, 0.364 | 0.731, 0.738, 0.755 | 1850 | 0.534 |
| Ottone (Brass) | 0.910, 0.778, 0.423 | 1 | 0.995, 0.974, 0.747 | 0.952, 0.979, 1.021 | 8600 | 0.780 |
| Cesio | 0.718, 0.554, 0.237 | 1 | 0.997, 1.002, 1.073 | 1.087, 1.180, 1.440 | 1886 | 0.566 |
| Cromo | 0.654, 0.685, 0.701 | 1 | 0.591, 0.675, 0.703 | 0.688, 0.728, 0.798 | 7200 | 0.680 |
| Cobalto | 0.699, 0.704, 0.671 | 1 | 0.731, 0.775, 0.715 | 0.727, 0.772, 0.823 | 8900 | 0.701 |
| Rame (Copper) | 0.932, 0.623, 0.522 | 1 | 0.999, 0.900, 0.744 | 0.982, 0.947, 0.945 | 8940 | 0.681 |
| Germanio | 0.500, 0.517, 0.465 | 1 | 0.068, 0.179, 0.002 | 0.620, 0.653, 0.701 | 5327 | 0.510 |
| Oro (Gold) | 1.059, 0.773, 0.307 | 1 | 1.001, 0.985, 0.523 | 0.971, 1.018, 0.994 | 19320 | 0.800 |
| Iridio | 0.745, 0.734, 0.704 | 1 | 0.818, 0.810, 0.727 | 0.759, 0.781, 0.810 | 22562 | 0.734 |
| Ferro (Iron) | 0.530, 0.513, 0.494 | 1 | 0.612, 0.541, 0.422 | 0.765, 0.767, 0.802 | 7870 | 0.515 |
| Piombo (Lead) | 0.626, 0.640, 0.693 | 1 | 0.717, 0.717, 0.696 | 0.758, 0.773, 0.799 | 11340 | 0.641 |
| Litio | 0.916, 0.890, 0.807 | 1 | 0.998, 0.995, 0.975 | 0.985, 0.998, 1.027 | 535 | 0.890 |
| Magnesio | 0.956, 0.953, 0.950 | 1 | 0.998, 0.996, 0.983 | 0.954, 0.964, 0.977 | 1737 | 0.953 |
| Manganese | 0.606, 0.592, 0.573 | 1 | 0.757, 0.761, 0.715 | 0.796, 0.834, 0.889 | 7476 | 0.594 |
| Mercurio | 0.781, 0.780, 0.778 | 1 | 0.901, 0.910, 0.890 | 0.813, 0.852, 0.902 | 13546 | 0.780 |
| Molibdeno | 0.589, 0.612, 0.594 | 1 | 0.495, 0.505, 0.383 | 0.683, 0.696, 0.726 | 10223 | 0.606 |
| Nichel (Nickel) | 0.697, 0.641, 0.563 | 1 | 0.855, 0.805, 0.675 | 0.815, 0.834, 0.871 | 8900 | 0.647 |
| Palladio | 0.734, 0.704, 0.662 | 1 | 0.874, 0.854, 0.779 | 0.811, 0.836, 0.872 | 12007 | 0.707 |
| Platino (Platinum) | 0.765, 0.730, 0.676 | 1 | 0.873, 0.850, 0.747 | 0.793, 0.815, 0.840 | 21450 | 0.734 |
| Potassio | 0.983, 0.956, 0.906 | 1 | 1.000, 1.000, 0.994 | 1.002, 1.011, 1.032 | 859 | 0.958 |
| Rubidio | 0.919, 0.859, 0.747 | 1 | 1.000, 0.999, 0.998 | 1.016, 1.042, 1.105 | 1534 | 0.864 |
| Silicio | 0.345, 0.369, 0.426 | 1 | 0.081, 0.000, 0.004 | 0.720, 0.701, 0.663 | 2330 | 0.368 |
| Argento (Silver) | 0.991, 0.985, 0.974 | 1 | 1.000, 1.000, 0.991 | 0.994, 0.995, 0.998 | 10500 | 0.985 |
| Sodio | 0.977, 0.962, 0.936 | 1 | 1.000, 1.000, 0.991 | 0.998, 1.002, 1.011 | 969 | 0.963 |
| Acciaio Inox (Stainless Steel) | 0.669, 0.639, 0.598 | 1 | 0.804, 0.791, 0.714 | 0.789, 0.823, 0.870 | 7500 | 0.642 |
| Titanio | 0.441, 0.400, 0.361 | 1 | 0.670, 0.641, 0.520 | 0.865, 0.906, 0.946 | 4540 | 0.406 |
| Titanio Anodizzato | 0.441, 0.400, 0.361 | 1 | 0.670, 0.641, 0.520 | 0.865, 0.906, 0.946 | 4540 | 0.406 |
| Tungsteno | 0.537, 0.536, 0.519 | 1 | 0.450, 0.409, 0.193 | 0.695, 0.704, 0.714 | 19300 | 0.535 |
| Vanadio | 0.534, 0.526, 0.546 | 1 | 0.474, 0.426, 0.175 | 0.705, 0.715, 0.695 | 6100 | 0.529 |
| Zinco | 0.808, 0.844, 0.865 | 1 | 0.854, 0.922, 0.923 | 0.762, 0.833, 0.896 | 7000 | 0.838 |

### 3.1 Note Critiche sui Metalli

**Oro**: il valore F0 del canale R supera 1.0 (1.059). Questo è fisicamente corretto poiché i valori F0 sono in spazio lineare e i metalli possono avere riflettanze superiori a 1.0 in certi canali spettrali. Nei renderer che usano sRGB come input, il clamp a 1.0 può introdurre errori di colore.

**Cesio e derivati**: valori F82 superiori a 1.0 (Cesio: 1.087, 1.180, 1.440). Questi metalli alcalini mostrano riflettanze anomale agli angoli rasanti. Fisicamente corretto ma richiedono renderer con supporto a HDR per la rappresentazione fedele.

**Argento vs Alluminio**: argento (0.985) è più luminoso dell'alluminio (0.922). Entrambi appaiono "cromati" ma con tonalità leggermente diverse: l'argento è più neutro, l'alluminio ha una leggera tinta fredda (canale B: 0.924).

**Silicio**: nonostante sia classificato come Metal nel database, il Silicio è tecnicamente un semiconduttore. I valori di riflettanza sono anomali (F0 canale B = 0.426, più alto di R e G) indicando un comportamento ottico non convenzionale.

---

## 4. DATABASE DEI VALORI FISICI — NON-METALLI {#4}

*Fonte: physicallybased.info — Dati in spazio lineare sRGB*
*Per i non-metalli il Metallic = 0 e il campo Specular Color è generalmente non definito (si applica la regola F0 = 0.04)*

| Materiale | Base Color F0 (R,G,B) | Metallic | Densità kg/m³ | Luminanza Rel. | Note |
|:----------|:----------------------|:---------|:--------------|:---------------|:-----|
| Asfalto fresco | 0.043, 0.041, 0.040 | 0 | — | 0.042 | Composito: pietrisco + bitume |
| Banana | 0.634, 0.532, 0.111 | 0 | — | 0.523 | |
| Lavagna (Blackboard) | 0.039, 0.039, 0.039 | 0 | — | 0.039 | |
| Sangue (Blood) | — | 0 | 1060 | — | Colore dipende da ossigenazione |
| Osso (Bone) | 0.793, 0.793, 0.664 | 0 | 1000 | 0.784 | |
| Mattone (Brick) | 0.262, 0.095, 0.061 | 0 | 500 | 0.128 | Densità molto variabile: 500–2400 |
| Cartone (Cardboard) | 0.351, 0.208, 0.110 | 0 | 700 | 0.231 | |
| Carota | 0.713, 0.170, 0.026 | 0 | — | 0.275 | |
| Carbone (Charcoal) | 0.020, 0.020, 0.020 | 0 | 200 | 0.020 | |
| Cioccolato | 0.162, 0.091, 0.060 | 0 | 1229 | 0.104 | |
| Cemento (Concrete) | 0.510, 0.510, 0.510 | 0 | 2400 | 0.510 | Valore neutro quasi-grigio |
| Diamante | — | 0 | 3500 | — | IOR = 2.417 |
| Guscio d'uovo (marrone) | 0.493, 0.248, 0.123 | 0 | — | 0.291 | |
| Guscio d'uovo (bianco) | 0.610, 0.624, 0.631 | 0 | — | 0.622 | |
| Erba (Grass) | 0.105, 0.133, 0.041 | 0 | — | 0.120 | |
| Gray Card | 0.180, 0.180, 0.180 | 0 | — | 0.180 | Standard 18% reflectance |
| Miele liquido | — | 0 | 1380 | — | IOR varia con contenuto d'acqua: 1.474–1.504 |
| Miele cristallizzato | 0.449, 0.319, 0.011 | 0 | 1380 | 0.324 | |
| Limone | 0.617, 0.366, 0.045 | 0 | — | 0.396 | |
| Marmo | 0.830, 0.791, 0.753 | 0 | 2700 | 0.797 | Materiale SSS |
| Latte (Milk) | 0.815, 0.813, 0.682 | 0 | 1026 | 0.804 | Materiale SSS |
| MIT Black | 0.000, 0.000, 0.000 | 0 | — | 0.000 | Nanotubi di carbonio — minimo teorico |
| Musou Black | 0.006, 0.006, 0.006 | 0 | — | 0.006 | Vernice più scura disponibile commercialmente |
| Carta (Office Paper) | 0.794, 0.834, 0.884 | 0 | 800 | 0.829 | Contiene optical brightener (fluorescenza UV) |
| Perla | 0.800, 0.750, 0.700 | 0 | 2700 | 0.757 | Materiale nacre/SSS — thin film |
| Porcellana | 0.745, 0.745, 0.723 | 0 | 2000 | 0.743 | |
| Sabbia (Sand) | 0.440, 0.386, 0.231 | 0 | 1440 | 0.386 | |
| Pelle I (chiara) | 0.847, 0.638, 0.552 | 0 | 1020 | 0.676 | Materiale SSS |
| Pelle II | 0.799, 0.485, 0.347 | 0 | 1020 | 0.542 | Materiale SSS |
| Pelle III | 0.623, 0.433, 0.343 | 0 | 1020 | 0.467 | Materiale SSS |
| Pelle IV | 0.436, 0.227, 0.131 | 0 | 1020 | 0.265 | Materiale SSS |
| Pelle V | 0.283, 0.148, 0.079 | 0 | 1020 | 0.172 | Materiale SSS |
| Pelle VI (scura) | 0.090, 0.050, 0.020 | 0 | 1020 | 0.056 | Materiale SSS |
| Neve (Snow) | 0.850, 0.850, 0.850 | 0 | 90 | 0.850 | |
| Spectralon | 0.990, 0.990, 0.990 | 0 | — | 0.990 | Massima riflettanza diffusa nota |
| Terracotta | 0.555, 0.212, 0.110 | 0 | 1800 | 0.278 | |
| Pneumatico (Tire) | 0.023, 0.023, 0.023 | 0 | — | 0.023 | |
| Dentifricio | 0.932, 0.937, 0.929 | 0 | 1300 | 0.935 | |
| Carta igienica | 0.830, 0.835, 0.784 | 0 | 20 | 0.830 | |
| Lavagna bianca (Whiteboard) | 0.869, 0.867, 0.771 | 0 | — | 0.860 | |

### 4.1 Range Critici dell'Albedo per i Dielettrici

Dalle misurazioni del database, il range validato per i non-metalli comuni è:
- **Minimo fisicamente plausibile**: ~0.020 (carbone, pneumatici, catrame)
- **Massimo fisicamente plausibile**: ~0.990 (Spectralon — caso estremo di laboratorio)
- **Range operativo per la gran parte dei materiali naturali**: **0.04 – 0.90** in spazio lineare (circa 54–240 in sRGB 8-bit)

I valori al di sotto di 0.04 (circa 54 sRGB) esistono ma sono riservati a materiali specifici (carbone: 0.020, pneumatico: 0.023, MIT Black: 0.000). **Un albedo nero puro (0,0,0) è fisicamente non plausibile per qualsiasi materiale naturale ad eccezione di MIT Black**, che è un materiale ingegnerizzato basato su nanotubi di carbonio.

---

## 5. INDICE DI RIFRAZIONE (IOR) — RIFERIMENTO COMPLETO {#5}

*Fonte: CGSociety IOR List (http://forums.cgsociety.org/t/a-complete-ior-list/1070401)*
*Valore IOR = n (parte reale dell'indice di rifrazione complesso)*
*Per i metalli, l'IOR è un numero complesso (n + ik) dove k è il coefficiente di estinzione. I valori sotto sono la parte reale n.*

### 5.1 Relazione IOR → F0

Il valore F0 di un dielettrico può essere calcolato dall'IOR con la formula di Fresnel:

```
F0 = ((n - 1) / (n + 1))²
```

Esempi pratici:
- IOR = 1.5 (vetro comune, plastica) → F0 = ((1.5-1)/(1.5+1))² = (0.5/2.5)² = 0.04
- IOR = 1.333 (acqua) → F0 ≈ 0.02
- IOR = 2.417 (diamante) → F0 ≈ 0.172

### 5.2 IOR — Materiali Comuni (selezione rilevante per CG)

| Materiale | IOR | F0 calcolato |
|:----------|:----|:-------------|
| Aria | 1.0003 | ~0.000 |
| Acqua (20°C) | 1.333 | ~0.020 |
| Ghiaccio | 1.309 | ~0.018 |
| Vetro Crown (comune) | 1.52 | ~0.043 |
| Vetro Flint leggero | 1.58 | ~0.051 |
| Vetro Flint pesante | 1.66 | ~0.063 |
| Quarzo | 1.544 | ~0.046 |
| Plastica | 1.460 | ~0.034 |
| Nylon | 1.53 | ~0.044 |
| Plexiglas/PMMA | 1.50 | ~0.040 |
| Diamante | 2.417 | ~0.172 |
| Zirconia cubica | 2.170 | ~0.132 |
| Rubino | 1.760 | ~0.072 |
| Zaffiro | 1.760 | ~0.072 |

### 5.3 IOR — Metalli (valori dalla lista CGS)

⚠️ **Nota critica**: Per i metalli, i valori IOR nella lista CGS sono la parte reale n dell'indice complesso. Non sono direttamente utilizzabili come F0 senza considerare anche il coefficiente di estinzione k. I valori F0 corretti per i metalli sono nel database della sezione 3.

| Metallo | IOR (n) nella lista CGS | F0 reale (dal db fisico) |
|:--------|:------------------------|:-------------------------|
| Alluminio | 1.44 | 0.922 |
| Rame (Copper) | 1.10 | 0.681 |
| Oro (Gold) | 0.47 | 0.800 |
| Argento (Silver) | 0.18 | 0.985 |
| Ferro (Iron) | 1.51 | 0.515 |
| Cromo | 2.97 | 0.680 |
| Platino | 2.33 | 0.734 |

**La discrepanza tra i valori IOR dei metalli nella lista CGS e i valori F0 del database fisico è normale e attesa**: i metalli hanno IOR complesso, e il valore che appare nella lista CGS è solo n (parte reale), non è il F0 che si usa nei renderer PBR. I renderer PBR usano direttamente F0, non IOR per i metalli.

### 5.4 IOR — Lista Completa (Fonte: CGSociety)

**Minerali e Gemme:**

| Materiale | IOR | Materiale | IOR |
|:----------|:----|:----------|:----|
| Acetone | 1.36 | Actinolite | 1.618 |
| Agata | 1.544 | Ambra | 1.546 |
| Ametista | 1.544 | Anatase | 2.490 |
| Andalusite | 1.641 | Apatite | 1.632 |
| Acquamarina | 1.577 | Aragonite | 1.530 |
| Asfalto | 1.635 | Azzurrite | 1.730 |
| Barite | 1.636 | Benzoite | 1.501 |
| Berillo | 1.577 | Calcite | 1.486 |
| Chalcedony | 1.530 | Gesso (Chalk) | 1.510 |
| Crisocolla | 1.500 | Corallo | 1.486 |
| Corindone | 1.766 | Diamante | 2.417 |
| Smeraldo | 1.576 | Fluorite | 1.434 |
| Vetro comune | 1.51714 | Ghiaccio | 1.309 |
| Giada Nefrite | 1.610 | Giadeite | 1.665 |
| Lapislazzuli | 1.61 | Malachite | 1.655 |
| Ossidiana | 1.489 | Opale | 1.450 |
| Perla | 1.530 | Quarzo | 1.544 |
| Quarzo fuso | 1.45843 | Roccia salina | 1.544 |
| Rubino | 1.760 | Zaffiro | 1.760 |
| Argento | 0.18 | Oro | 0.47 |
| Acciaio | 2.50 | Solfuro | 1.960 |
| Titanio | 2.16 | Acqua 20°C | 1.33335 |
| Zircone alto | 1.960 | Zircone basso | 1.800 |
| Zirconia cubica | 2.170 | | |

**Liquidi:**

| Materiale | IOR |
|:----------|:----|
| Acetone | 1.36 |
| Alcool etilico | 1.36 |
| Birra | 1.345 |
| Glicerina | 1.473 |
| Miele (13% acqua) | 1.504 |
| Miele (17% acqua) | 1.494 |
| Miele (21% acqua) | 1.484 |
| Latte | 1.35 |
| Olio vegetale (50°C) | 1.47 |
| Olio safflower | 1.466 |
| Acqua (0°C) | 1.33346 |
| Acqua (20°C) | 1.33283 |
| Acqua (100°C) | 1.31766 |

---

## 6. DATI SPETTRALI — SpectralDB {#6}

*Fonte: SpectralDB (Jakubiec, J.A. — Spectral Materials Database)*
*Metodologia: misurazioni spettrofotometriche in loco*
*Formato SCI: Specular Component Included | SCE: Specular Component Excluded*

### 6.1 Struttura dei Dati SpectralDB

Il database SpectralDB contiene misurazioni reali di riflettanza spettrale su materiali architettonici e di arredamento. Ogni entry contiene:

- **RGB (8-bit)**: colore approssimato
- **L\*a\*b\***: rappresentazione CIELab perceptually uniform
- **SCI Measures**: riflettanza spettrale con componente speculare inclusa (360–740nm, step 10nm)
- **SCE Measures**: riflettanza spettrale con componente speculare esclusa
- **Specularity**: livello di specularità relativa (0.01–2.05 nel campione osservato)
- **Roughness**: stima della rugosità superficiale (0.2–0.3 nel campione osservato)

### 6.2 Significato dei Parametri SCI vs SCE

**SCI (Specular Component Included)**: misura la riflessività totale della superficie, includendo sia la riflessione diffusa che quella speculare. Corrisponde alla riflettanza totale di energia.

**SCE (Specular Component Excluded)**: misura solo la componente diffusa, escludendo il picco speculare. Corrisponde all'Albedo nel senso PBR più stretto.

**In produzione CG**: il valore SCE è generalmente più appropriato come riferimento per il canale Base Color/Albedo, poiché il canale speculare è gestito separatamente da Roughness + F0 nel workflow Metallic-Roughness.

### 6.3 Campioni rappresentativi SpectralDB

| ID | Materiale | Tipo | R,G,B (8-bit) | Specularity | Roughness |
|:---|:----------|:-----|:--------------|:------------|:----------|
| 1 | Pareti bianche | Muro | 138,135,120 | 0.36 | 0.2 |
| 2 | Piastrelle grigio scuro | Pavimento | 33,31,28 | 2.05 | 0.2 |
| 1288 | Intonaco bianco CH | Muro | 146,144,135 | 0.22 | 0.3 |
| 1289 | Intonaco bianco NL | Muro | 135,132,117 | 0.01 | 0.3 |
| 1290 | Parete plastica bianca NL | Muro | 143,142,139 | 0.09 | 0.3 |

### 6.4 Osservazioni sulla Specularity nei dati SpectralDB

Il valore di Specularity nel database SpectralDB non è equivalente al F0 del PBR. È un indice relativo della brillantezza superficiale misurata dallo strumento. Valori superiori a 1.0 (come 2.05 per le piastrelle grigio scuro) indicano superfici molto brillanti con forte componente speculare — tipico di superfici ceramiche lucidate.

---

## 7. GESTIONE DEL COLORE E SPAZI COLORE {#7}

### 7.1 sRGB vs Linear

**sRGB** è uno spazio colore perceptually encoded: è ottimizzato per la visualizzazione su monitor, non per i calcoli matematici. La gamma correction applicata dallo spazio sRGB comprime le ombre e espande le alte luci.

**Linear** (spazio lineare) è lo spazio matematicamente corretto per i calcoli fisici. Tutta la matematica del PBR deve avvenire in spazio lineare.

**Regola fondamentale**:
- **Mappe di colore** (Albedo, Emissive) → **sRGB**: contengono informazione percettiva
- **Mappe di dati** (Normal, Roughness, Metallic, AO, Height, Displacement) → **Linear/Raw**: contengono dati matematici

**Errore gamma comune**: importare una Normal Map come sRGB. Lo spazio sRGB applica una curva di gamma alle normali, trasformando vettori matematicamente corretti in vettori distortia. Il risultato sono shading errati visibili come artefatti o sfaccettature anomale.

### 7.2 CIELab come spazio di validazione

Il database SpectralDB usa CIELab (L\*a\*b\*) come rappresentazione intermedia. Questo spazio ha caratteristiche utili per la validazione PBR:
- **L\***: luminosità percepita (0 = nero assoluto, 100 = bianco perfetto)
- **a\***: asse verde-rosso
- **b\***: asse blu-giallo

Per la validazione PBR, L\* fornisce un riferimento indipendente dalla calibrazione del monitor per valutare se un albedo è fisicamente plausibile.

---

## 8. TIPOLOGIE DI MAPPE TEXTURE E LORO RUOLO PBR {#8}

### 8.1 Albedo / Base Color

Definisce il colore diffuso del materiale (per i dielettrici) o il colore di riflettanza speculare (per i metalli). Lo spazio colore corretto è **sRGB**.

Limitazioni fisiche:
- Nessun materiale naturale ha albedo perfettamente nera (0,0,0) o perfettamente bianca (1,1,1)
- Range operativo validato: 0.04–0.90 in lineare (54–240 in sRGB 8-bit)
- **Non deve contenere**: ombre baked, AO baked, illuminazione baked, informazioni di luce direzionale

### 8.2 Normal Map

Codifica la direzione delle normali superficiali in tangent space. Lo spazio colore corretto è **Linear/Raw**.

- Canali R e G codificano X e Y (vettori tangenziali)
- Il canale B viene ricostruito matematicamente dal renderer: B = sqrt(1 - R² - G²)
- Valore neutro (superficie piatta): R=128, G=128, B=255 (in 8-bit sRGB)

**DirectX vs OpenGL convention**: il canale G è invertito tra le due convenzioni:
- DirectX (UE5): G basso = going up. Normal map Y-up
- OpenGL (Unity, Godot): G alto = going up. Normal map Y-down

### 8.3 Roughness

Descrive la distribuzione delle microfaccette. Valori tra 0.0 (specchio) e 1.0 (completamente opaco). Spazio colore: **Linear**.

- Per molti materiali metallici: 0.1–0.7 (dipende dall'usura)
- Per materiali ceramici lucidati: 0.0–0.2
- Per materiali opachi (cemento, pietra non levigata): 0.7–1.0

**Nota**: in alcuni tool (Substance, Unreal Specular Gloss), viene usato **Glossiness = 1 - Roughness**.

### 8.4 Metallic

Canale binario: 0 per dielettrici, 1 per metalli. Spazio colore: **Linear**.

I valori intermedi (0.1–0.9) possono essere fisicamente motivati solo per:
- Superfici con transizione tra area metallica e area ossidata
- Texture con dettaglio fine che mescola pixel metallici e dielettrici
- Metalli fortemente ossidati

Per i metalli puri, il valore dovrebbe essere esattamente 1.0. Per i dielettrici puri, 0.0.

### 8.5 Ambient Occlusion (AO)

Simula l'occlusione della luce ambientale in cavità e rientranze. Spazio colore: **Linear**.

L'AO non è una mappa "fisicamente basata" nel senso stretto — è un'approssimazione stilistica. Il suo impatto sulla correttezza PBR è dibattuto: applicata all'illuminazione diretta può creare violazioni fisiche; applicata solo all'illuminazione ambientale è fisicamente giustificabile.

### 8.6 Height / Displacement

Codifica l'altezza geometrica. Spazio colore: **Linear**.

- 8-bit (0–255): precisione bassa, visibile "banding" nelle aree di transizione graduale
- 16-bit (0–65535): precisione alta, raccomandato per displacement realistico
- 32-bit float (EXR): massima precisione, necessario per dati di scansione fotogrammetrica

### 8.7 Emissive

Codifica la luce emessa dalla superficie. Spazio colore: **sRGB** per il colore, ma i valori possono superare 1.0 (HDR).

### 8.8 Packed Maps (ORM, ARM, RMA)

Combinano più canali di dati in una singola texture RGBA per ridurre il numero di sampler:
- **ORM**: R=Occlusion, G=Roughness, B=Metallic (Unity HDRP MaskMap variant)
- **ARM**: A=Ambient Occlusion, R=Roughness, M=Metallic
- **RMA**: R=Roughness, G=Metallic, B=Ambient Occlusion (variante comune UE5)

---

## 9. FORMATI FILE — CLASSIFICAZIONE TECNICA {#9}

*Fonte: File Type Research (documenti di ricerca DVAMOCLES)*

### 9.1 Formati di Authoring (Lossless — Alta Fedeltà)

| Formato | Bit depth | Canali | Utilizzo ideale | Vantaggi | Svantaggi |
|:--------|:----------|:-------|:----------------|:---------|:----------|
| TGA (.tga) | 8-bit | RGBA | Normal, Albedo, Mask | Standard industriale, alpha preciso, nessun artefatto | No HDR, file pesanti |
| TIFF (.tif) | 16-bit (sweet spot) fino a 32-bit | Multi | Height, Displacement | Assenza di banding, leggibile da XMP | Varianti compressione caotiche (LZW, Zip, Packbits) |
| PNG (.png) | 8 o 16-bit | RGBA | Albedo, UI, Maschere | Compressione lossless, universale | Pre-moltiplicazione alpha può corrompere dati PBR |
| EXR (.exr) | 32-bit float | Multi-layer | HDR, dati grezzi, HDRI | Floating point, infiniti canali, fedeltà cromatica massima | Peso su disco estremo |
| HDR (.hdr) | 32-bit | RGB | HDRI legacy | Compatibilità con librerie datate | Meno efficiente di EXR |
| JPG (.jpg) | 8-bit | RGB | — | Peso su disco minimo | **Compressione lossy distruttiva** — inadatto per dati PBR |
| BMP (.bmp) | 8-bit | RGB | Legacy | Compatibilità legacy | Nessuna alpha, nessuna compressione |

### 9.2 Analisi del Rischio PNG per Dati PBR

Il formato PNG applica la **pre-moltiplicazione dell'alpha**: i valori nei canali RGB vengono moltiplicati per il valore alpha prima di scrivere su disco. Questo può causare corruzioni silenziose:

**Esempio**: una Roughness Map usata come canale Alpha di una texture RGBA PNG. Se l'immagine ha trasparenza parziale in certe aree, quei pixel avranno i valori RGB compressi verso zero anche se la Roughness non dovrebbe essere zero in quelle aree.

**Soluzione**: usare TGA per texture che combinano dati PBR in canali RGBA, o assicurarsi che il canale Alpha PNG sia sempre opaco (255) quando si usano gli altri canali come dati.

### 9.3 Formati Container Proprietari

**PSD (.psd)**: contiene Layer, Gruppi, Maschere di livello, Livelli di regolazione. Esistono librerie open-source per leggere i layer senza Adobe Photoshop. Utilità principale: mappare gruppi di layer a canali PBR diversi durante l'importazione.

**SBSAR (.sbsar)**: archivio Substance compilato. Contiene algoritmi procedurali e parametri esposti. Richiede Substance Engine SDK per essere eseguito. Non è una texture statica — genera texture al momento dell'esecuzione con parametri configurabili.

**UASSET (.uasset)**: texture compressa di Unreal Engine. Contiene texture BCn + Mipmaps + metadati del motore (Texture Group, streaming). Può essere decompressa per accedere ai dati raster originali.

### 9.4 Formati Engine-Ready (GPU Compressed)

**DDS (.dds)**: DirectDraw Surface. Container per DirectX/Unreal. Contiene texture già compresse in formato BCn (BC1–BC7). Il file DDS è direttamente leggibile dalla GPU senza decompressione CPU.

**KTX2 (.ktx2)**: Khronos Texture 2. Standard moderno per Vulkan/glTF. Supporta la super-compressione Basis Universal (transcodifica in formato GPU-specifico al caricamento).

---

## 10. COMPRESSIONE GPU — STANDARD BCn {#10}

*Fonte: File Type Research*

### 10.1 Tabella dei Formati BC (Block Compression)

| Formato | Alias | Canali compressi | Rapporto compressione | Qualità | Uso ottimale |
|:--------|:------|:-----------------|:----------------------|:--------|:-------------|
| BC1 | DXT1 | RGB (+ 1-bit alpha opzionale) | 6:1 | Bassa — artefatti visibili su gradienti | Albedo senza alpha, dettaglio basso |
| BC2 | DXT3 | RGBA (4-bit alpha) | 4:1 | Media — alpha "stepped" | Raro |
| BC3 | DXT5 | RGBA (8-bit alpha) | 4:1 | Media | Texture con alpha di qualità |
| BC4 | — | Singolo canale | 2:1 | Alta su singolo canale | Heightmap, AO standalone, canali singoli |
| BC5 | — | RG (due canali) | 2:1 | Alta su R+G, B ricostruito | **Normal Map** — standard raccomandato |
| BC6H | — | RGB HDR (floating point) | 6:1 | Alta su HDR | HDR texture, HDRI |
| BC7 | — | RGBA | 4:1 | Alta — migliore qualità lossless tra BC | Albedo di qualità, Packed Maps, UI |

### 10.2 BC5 per le Normal Map — Dettaglio Tecnico

BC5 comprime i soli canali R e G. Il canale B viene **ricostruito matematicamente** dal renderer durante la lettura della texture:

```
B = sqrt(1.0 - R² - G²)
```

Questo funziona perché le normali in tangent space sono vettori normalizzati: |N| = 1. Conoscendo R e G, B è univocamente determinato (assumendo B sempre positivo, cioè la normale punta verso l'osservatore).

**Vantaggio**: nessuna perdita di qualità rispetto a BC7 per le Normal Map, a parità di dimensione su disco dimezzata.
**Limitazione**: richiede che il renderer ricostruisca B — non tutti i motori supportano questo (richiede shader specifico).

### 10.3 BC7 — Standard Moderno

BC7 è il formato raccomandato per texture di alta qualità che richiedono RGBA completo. A differenza di BC3 (DXT5), BC7 usa un algoritmo di compressione adattivo che valuta ogni blocco 4×4 pixel e sceglie la codifica ottimale tra 8 modalità diverse. Risultato: qualità significativamente superiore a BC3 per lo stesso bit rate.

**Casi d'uso prioritari per BC7**:
- Albedo/Base Color di alta qualità
- Packed Maps (ORM, RMA) dove tutti i canali contengono dati critici
- Texture UI con gradienti fini
- MaterialControl o qualsiasi packed RGBA dove la qualità di tutti i 4 canali è essenziale

**Confronto con alternatives**:
- BC7 vs PNG: PNG è lossless su disco ma non è compresso per GPU. Una texture PNG da 1024×1024 RGBA occupa 4MB in VRAM; la stessa in BC7 occupa ~0.5MB
- BC7 vs TGA (in VRAM): stesso rapporto — TGA non compresso occupa circa 8× più VRAM di BC7

---

## 11. REGOLE DI VALIDAZIONE PBR {#11}

### 11.1 Regole Universali (Applicabili a Tutti i Materiali)

**R01 — Conservazione dell'Energia**: nessun canale diffuso o speculare può superare 1.0 in spazio lineare. Se Albedo + Specular > 1.0, il materiale emette più luce di quella ricevuta — violazione fisica grave.

**R02 — Gamma Corretto**: le mappe di dati (Normal, Roughness, Metallic, AO, Height) devono essere in spazio lineare. Le mappe di colore (Albedo, Emissive) devono essere in sRGB.

**R03 — Normal Map Normalizzata**: i vettori normali devono essere normalizzati (|N| = 1). Vettori con lunghezza diversa da 1.0 producono shading errati.

**R04 — Metallic Binario**: il canale Metallic ideale è binario (0 o 1). Valori intermedi sono fisicamente giustificati solo in transizioni di materiale (ossidazione, sporco su metallo).

**R05 — No Lighting Information in Albedo**: l'Albedo non deve contenere ombre baked, illuminazione direzionale, riflessi o AO. Questi dati "confondono" il renderer che aggiunge la sua illuminazione sopra.

### 11.2 Regole per Metalli

**R06 — Albedo Metalli**: i metalli puri hanno Base Color che rappresenta il colore di riflessione, non diffuso. Il valore tipico è alto (0.5–1.0 in lineare) e può avere tinta cromatica (Oro: alto-R, basso-B).

**R07 — No Diffuse Color in Metalli Puri**: con Metallic = 1, la componente diffusiva dovrebbe essere zero. Se un renderer non applica correttamente questo principio, il Base Color dei metalli viene interpretato erroneamente come colore diffuso.

**R08 — F0 Alto per Metalli**: il valore F0 dei metalli è sempre > 0.5 in spazio lineare. Un metallo con F0 < 0.3 non è fisicamente plausibile come metallo puro.

### 11.3 Regole per Dielettrici

**R09 — Albedo Range**: il range fisicamente valido per la maggior parte dei dielettrici è 0.04–0.90 in spazio lineare (54–240 in sRGB 8-bit). Valori inferiori a 0.04 sono fisicamente possibili solo per materiali ultra-assorbenti (carbone, pneumatici). Valori superiori a 0.90 sono fisicamente possibili solo per materiali ultra-riflettenti (neve fresca, Spectralon).

**R10 — F0 Costante**: la maggior parte dei dielettrici ha F0 = 0.04 (corrisponde a IOR ≈ 1.5). Questo è il valore default per vetro comune, plastica, pietra, legno, tessuto.

**R11 — Specularity Dielettrici**: il canale Specular (se separato da Metallic) nei dielettrici dovrebbe stare nell'intervallo 0.35–0.5 in spazio sRGB (equivalente a F0 0.02–0.06) per la grande maggioranza dei materiali.

### 11.4 Regole per i Formati File

**R12 — No JPG per Dati PBR**: la compressione lossy del JPG introduce artefatti che corrompono silenziosamente le Normal Map, Roughness e altri canali di dati. Solo l'Albedo può tollerare JPG come format temporaneo.

**R13 — Heightmap a 16-bit Minimo**: le Heightmap a 8-bit producono "banding" visibile nelle aree di transizione graduale. Il minimo raccomandato per dati di displacement è 16-bit (TIFF o PNG 16-bit).

**R14 — Normal Map non sRGB**: le Normal Map devono essere importate come Linear/Raw, non come sRGB. L'errore gamma trasforma i vettori, producendo shading falsati.

**R15 — Export GPU**: per i motori real-time (UE5, Unity), le texture finali devono essere in formato BC compresso. PNG e TGA non compressi sono accettabili come sorgenti ma occupano 4–8× più VRAM rispetto ai formati BC.

---

## 12. DOMANDE PER LA PARTE 2 {#12}

Le seguenti domande identificano le aree tematiche che questa Knowledge Base non copre e che richiedono l'integrazione di ulteriori documenti nella Parte 2.

### 12.1 Domande sui Principi Fisici Avanzati

1. **Thin-Film Interference**: quali sono le regole fisiche per modellare bolle di sapone, perle nacre e titanio anodizzato? Come si traducono in parametri shader per renderer real-time?

2. **Subsurface Scattering (SSS)**: il database identifica 6 toni di pelle, marmo, latte, cera come materiali SSS. Quali sono i parametri fisici (scatter distance, absorption coefficient, anisotropy factor) di questi materiali? Come si integrano nel workflow PBR standard?

3. **Prismatici e Dispersione**: il diamante ha IOR 2.417 ma il fenomeno della dispersione cromatica (rainbow effect) richiede IOR diversi per ogni lunghezza d'onda. Quali sono i valori Cauchy o Sellmeier per i materiali gemologici comuni?

4. **IOR Complesso per i Metalli**: nella lista CGS, alcuni metalli hanno IOR < 1 (Oro: 0.47, Argento: 0.18). Questo è fisicamente corretto e implica che il valore riportato è n (parte reale). Quali sono i valori di k (coefficiente di estinzione) per questi stessi metalli, necessari per il calcolo completo della riflettanza di Fresnel?

### 12.2 Domande sullo Spazio Colore

5. **ACEScg vs sRGB**: il workflow ACES (Academy Color Encoding System) sta diventando standard in VFX e in alcuni giochi AAA. Come differisce la gestione dell'Albedo in ACEScg rispetto a sRGB? Come si convertono i valori F0 tra i due spazi?

6. **Pointer's Gamut**: alcuni database (Charcoal: Lagarde, "Feeding a Physically Based Shading Model") citano Pointer's Gamut come riferimento per l'albedo dei materiali reali. Qual è l'area del Pointer's Gamut e come definisce il bound dell'albedo fisicamente plausibile nel diagramma CIE?

7. **Optical Brighteners (OFP)**: la carta da ufficio nel database ha valori anomali nel canale B (0.884 > R=0.794), indicando fluorescenza UV. Come si modella correttamente questo comportamento in PBR (emissive supplementare, shader specifici)?

### 12.3 Domande sui Materiali Specifici

8. **Car Paint Multi-Layer**: il database identifica Car Paint con Base Color 0.1 e include flake metalliche. Quali sono le regole per i clearcoat multi-layer (basecoat + clearcoat)? Come si differenzia il roughness del clearcoat da quello del basecoat?

9. **Legno e Materiali Fibrosi**: il database non include dati espliciti per il legno come materiale. Qual è il range di albedo per le specie legnose più comuni (quercia, pino, ebano, frassino)? Qual è il range di Roughness fisicamente validato per legno grezzo vs levigato vs verniciato?

10. **Materiali Traslucidi**: vetro, ghiaccio, diamante hanno Metallic = 0 ma non sono opachi. Il workflow Metallic-Roughness standard non cattura la trasmissione della luce. Quali shader/workflow alternativi (Refraction, Translucency) sono necessari per questi materiali?

### 12.4 Domande sui Formati e Standard Emergenti

11. **OpenPBR e MaterialX**: il database fisico cita Portsmouth, Kutz, Hill (2025) "OpenPBR: Novel Features and Implementation Details". Qual è il nuovo set di parametri introdotto da OpenPBR rispetto al workflow Metallic-Roughness standard? Come si mappano i parametri F0/F82 presenti nel database a quelli di OpenPBR?

12. **UE5 Substrate**: il sistema Substrate di Unreal Engine 5.7 introduce una nuova struttura del materiale basata su "slab" fisici con parametri come Diffuse Albedo, F0, F90. Come si mappano i dati del database fisico (F0, F82, Metallic) ai parametri Substrate?

13. **KTX2 e Basis Universal**: il formato KTX2 con super-compressione Basis Universal supporta la transcodifica runtime verso BC1–BC7, ASTC, ETC. Qual è il processo di preparazione e ottimizzazione dei file per questo formato? Quali tool open-source sono disponibili?

14. **ASTC per Mobile**: per piattaforme mobile (iOS/Android), ASTC (Adaptive Scalable Texture Compression) è lo standard de facto. Quali sono i block size e quality mode ottimali per le diverse tipologie di mappe PBR su mobile?

### 12.5 Domande sulla Validazione

15. **Histogram-Based Validation**: i documenti citano la PBR Sanity Check tramite istogramma. Quali sono le soglie operative precise (in 8-bit sRGB e in lineare) per classificare un albedo come "fuori range" per le categorie di materiali comuni (metalli, dielettrici chiari, dielettrici scuri)?

16. **Normal Map Quality Metrics**: oltre alla normalizzazione dei vettori, esistono metriche quantitative per valutare la qualità di una Normal Map (smoothness, frequency distribution, absence of artifacts)? Quali soglie numeriche indicano una Normal Map problematica?

---

*Fine Documento — PBR Master Knowledge Base Parte 1*
*Versione: 1.0 | Data: 2026-04-11*
*Fonti integrate: Physically Based Database (physicallybased.info), SpectralDB (Jakubiec), IOR List (CGSociety), File Type Research*
