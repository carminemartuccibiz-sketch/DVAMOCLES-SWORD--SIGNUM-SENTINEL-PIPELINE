# run_pipeline.py (root project)

import json
from core.pipeline import run_pipeline

if __name__ == "__main__":
    data = run_pipeline("01_RAW_ARCHIVE")

    with open("04_DATASET/dataset.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("Dataset generato in 04_DATASET/")