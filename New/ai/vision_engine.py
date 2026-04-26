import gc
import logging
from typing import Optional

try:
    import torch
    from PIL import Image
    from transformers import BlipForConditionalGeneration, BlipProcessor

    HAS_VISION_LIBS = True
except ImportError:
    torch = None  # type: ignore
    Image = None  # type: ignore
    BlipProcessor = None  # type: ignore
    BlipForConditionalGeneration = None  # type: ignore
    HAS_VISION_LIBS = False


class VisionEngine:
    """BLIP-based captions for PBR textures (lazy load)."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("SIGNUM_SENTINEL.VISION")
        self.device = "cuda" if HAS_VISION_LIBS and torch is not None and torch.cuda.is_available() else "cpu"
        self.processor: Optional["BlipProcessor"] = None
        self.model: Optional["BlipForConditionalGeneration"] = None
        self.ontology = {
            "SMOOTH": "Superficie levigata, bassa frequenza spaziale rilevata nei pixel.",
            "ROUGH": "Alta variazione di contrasto locale, indica porosità o usura.",
            "METALLIC": "Rilevata firma spettrale conduttiva; riflessi tinti dall'albedo.",
            "ORGANIC": "Pattern asimmetrici e naturali (es. terra, pelle, vegetazione).",
            "GEOMETRIC": "Rilevate linee rette o angoli definiti (es. mattoni, piastrelle).",
            "HIGH_FREQ": "Dettagli superficiali molto fini, richiede filtri anistropici alti.",
        }

    def load(self) -> bool:
        if not HAS_VISION_LIBS:
            self.logger.warning("Vision libs non disponibili (torch/transformers).")
            return False
        if self.model is not None and self.processor is not None:
            return True
        try:
            self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            ).to(self.device)
            self.logger.info("Vision AI caricata su %s", self.device)
            return True
        except Exception as exc:
            self.logger.error("Errore caricamento Vision AI: %s", exc)
            self.processor = None
            self.model = None
            return False

    def unload(self) -> None:
        try:
            self.model = None
            self.processor = None
            gc.collect()
            if HAS_VISION_LIBS and torch is not None and torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception as exc:
            self.logger.error("Errore unload Vision AI: %s", exc)

    def see_material(self, image_path: str) -> str:
        if not self.load() or Image is None:
            return ""
        try:
            raw_image = Image.open(image_path).convert("RGB")
            inputs = self.processor(
                raw_image, "a technical photo of a PBR material showing", return_tensors="pt"
            ).to(self.device)
            with torch.no_grad():
                out = self.model.generate(**inputs)
            return self.processor.decode(out[0], skip_special_tokens=True).capitalize()
        except Exception:
            self.logger.exception("see_material failed")
            return ""

    def explain_tag(self, tag: str) -> str:
        return self.ontology.get(tag.upper(), "Tag identificato tramite analisi euristica.")
