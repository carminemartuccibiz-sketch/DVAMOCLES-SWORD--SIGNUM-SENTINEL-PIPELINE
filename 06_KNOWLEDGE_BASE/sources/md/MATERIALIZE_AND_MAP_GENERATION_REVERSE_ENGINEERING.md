# Materialize and Map Generation Reverse Engineering

## Scope
- Objective: document how extra PBR maps are generated from color/albedo, with focus on `Materialize` integration and internal fallback algorithms.
- Policy: generated maps are **custom extras** and do not replace provider RAW maps.

## Pipeline Behavior
- Input source map: `ALBEDO/COLOR/BASECOLOR`.
- Target maps generated: `NORMAL`, `ROUGHNESS`, `AO`, `HEIGHT`, `CAVITY`.
- External-first strategy:
  - try `ExternalGeneratorHook` (Materialize/toolchain)
  - if external call fails/unavailable, fallback to internal OpenCV generators
- For RAW materials:
  - generated maps are exported to `02_CUSTOM/<provider>/<material>/variants/<variant>_GEN`
  - RAW variant remains untouched

## Internal Algorithms (OpenCV Fallback)

### Normal map generation
- Convert albedo to grayscale.
- Apply Gaussian blur to reduce pixel noise.
- Compute Sobel derivatives (`dx`, `dy`) as surface slope approximation.
- Build pseudo-normal vector `N = normalize([-dx, -dy, 1])`.
- Remap from `[-1, 1]` to `[0, 255]`.
- Output: tangent-like normal approximation, useful for synthetic training data.

### Roughness generation
- Convert to grayscale.
- Invert luminance.
- Min-max normalize to `[0,255]`.
- Heuristic interpretation:
  - brighter albedo zones -> smoother tendency after inversion
  - darker albedo zones -> rougher tendency

### Ambient Occlusion (AO) generation
- Convert to grayscale.
- Strong Gaussian blur as macro cavity proxy.
- Invert blurred image and normalize.
- Result approximates broad concavity shadowing, not true ray-traced AO.

### Height generation
- Convert to grayscale.
- Apply histogram equalization.
- Enhances local contrast as pseudo-height field.
- Best used as training signal, not physically measured displacement.

### Cavity generation
- Convert to grayscale.
- Light blur then Laplacian edge response.
- Use absolute Laplacian magnitude.
- Normalize to `[0,255]`.
- Emphasizes fine creases and micro-relief structures.

## External Materialize Integration Notes
- The hook resolves `Materialize` executable from configured directory.
- Invocation is toolchain-compatible (external command bridge).
- If the external process does not produce the output file, pipeline falls back automatically.
- `generator_details` in file records stores:
  - command
  - return code
  - stdout/stderr tail
  - status (`ok/failed/error/disabled`)

## Data Semantics for AI Training
- RAW = provider original data.
- CUSTOM = generated/modified/derived data.
- Generated maps from RAW are attached as additional custom supervision:
  - preserve RAW fidelity for ground truth
  - add synthetic pairs for augmentation and reverse learning tasks

## Known Limits
- Grayscale-derived maps cannot infer true physical microstructure.
- Sobel/Laplacian methods are local operators; global material priors are not modeled.
- Color-to-roughness mapping is heuristic and domain-dependent.

## Suggested AI Usage
- Use RAW as primary target labels.
- Use CUSTOM generated maps as auxiliary channels:
  - pretraining
  - consistency losses
  - ablation datasets (provider vs generated comparison)
