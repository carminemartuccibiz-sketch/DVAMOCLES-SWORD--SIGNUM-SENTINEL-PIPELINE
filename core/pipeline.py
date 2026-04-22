# core/pipeline.py

from core.ingestor import Ingestor
from core.metadata_extractor import extract_metadata
from core.naming_intelligence import NamingIntelligence

ni = NamingIntelligence()

def enrich_material_sets(material_sets: list):

    for mat in material_sets:
        for variant in mat["variants"]:
            for f in variant["files"]:

                path = f["path"]

                # METADATA
                metadata = extract_metadata(path)
                f["metadata"] = metadata

                # NAMING
                naming = ni.classify(f["filename"])
                f["map_type"] = naming.map_type
                f["map_confidence"] = naming.confidence
                f["normal_format"] = naming.convention

    return material_sets


def run_pipeline(root="01_RAW_ARCHIVE"):

    ingestor = Ingestor(root)
    result = ingestor.scan()

    enriched = enrich_material_sets(result["materials"])

    return {
        "materials": enriched,
        "summary": result["summary"]
    }