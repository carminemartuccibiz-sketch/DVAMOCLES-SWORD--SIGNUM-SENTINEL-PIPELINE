import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
import logging

class VisionEngine:
    """Motore AI per la descrizione semantica dei materiali e spiegazione dei tag."""
    
    def __init__(self):
        self.logger = logging.getLogger("SENTINEL.VISION")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Caricamento modello leggero per Image-to-Text
        try:
            self.processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            self.model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(self.device)
            self.logger.info(f"Vision AI caricata su {self.device}")
        except Exception as e:
            self.logger.error(f"Errore caricamento Vision AI: {e}")

        # Ontologia dei Tag per il Reasoning
        self.ontology = {
            "SMOOTH": "Superficie levigata, bassa frequenza spaziale rilevata nei pixel.",
            "ROUGH": "Alta variazione di contrasto locale, indica porosità o usura.",
            "METALLIC": "Rilevata firma spettrale conduttiva; riflessi tinti dall'albedo.",
            "ORGANIC": "Pattern asimmetrici e naturali (es. terra, pelle, vegetazione).",
            "GEOMETRIC": "Rilevate linee rette o angoli definiti (es. mattoni, piastrelle).",
            "HIGH_FREQ": "Dettagli superficiali molto fini, richiede filtri anistropici alti."
        }

    def see_material(self, image_path: str) -> str:
        """Genera una descrizione testuale tecnica del file."""
        try:
            raw_image = Image.open(image_path).convert('RGB')
            inputs = self.processor(raw_image, "a technical photo of a PBR material showing", return_tensors="pt").to(self.device)
            out = self.model.generate(**inputs)
            return self.processor.decode(out[0], skip_special_tokens=True).capitalize()
        except:
            return "Descrizione non disponibile."

    def explain_tag(self, tag: str) -> str:
        """Fornisce la motivazione tecnica dietro un tag assegnato."""
        return self.ontology.get(tag.upper(), "Tag identificato tramite analisi euristica.")
