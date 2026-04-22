import os
import shutil
import json
import requests
from pathlib import Path

# -------------------------
# CONFIG
# -------------------------

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"

RAW_DIR = Path("01_RAW_ARCHIVE")
CUSTOM_DIR = Path("02_CUSTOM")
TEMP_DIR = Path("temp/import_batch")

VALID_EXT = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".exr"]

# -------------------------
# AI
# -------------------------

def ask_ai(prompt):
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
        )
        return r.json()["response"]
    except:
        return None

def interpret_process(description):
    prompt = f"""
Convert this into structured JSON pipeline.

{description}

Output JSON only:
{{
 "pipeline":[{{"step":"","tool":"","input":"","output":"","notes":""}}]
}}
"""
    result = ask_ai(prompt)

    try:
        return json.loads(result)
    except:
        return {"raw_text": description}

# -------------------------
# USER INPUT HELPERS
# -------------------------

def ask(msg):
    return input(f"\n{msg}\n> ").strip()

def choose(options):
    for i, opt in enumerate(options):
        print(f"{i}: {opt}")
    idx = int(input("> "))
    return options[idx]

# -------------------------
# SESSION DATA
# -------------------------

materials = {}

def get_or_create_material():
    name = ask("Material name?")

    if name not in materials:
        provider = ask("Provider? (es: AmbientCG, Custom, Poliigon)")
        materials[name] = {
            "provider": provider,
            "raw_files": [],
            "custom_files": [],
            "process": None
        }

    return name

# -------------------------
# FILE ASSIGNMENT
# -------------------------

def process_files(files):

    for f in files:

        print("\n" + "="*50)
        print(f"FILE: {f.name}")
        print("="*50)

        action = ask(
            "Action?\n"
            "1 = RAW\n"
            "2 = CUSTOM\n"
            "3 = SKIP"
        )

        if action == "3":
            continue

        mat_name = get_or_create_material()

        if action == "1":
            materials[mat_name]["raw_files"].append(f)

        elif action == "2":
            materials[mat_name]["custom_files"].append(f)

# -------------------------
# SAVE RAW
# -------------------------

def save_raw():

    for mat, data in materials.items():

        if not data["raw_files"]:
            continue

        target = RAW_DIR / data["provider"] / mat
        target.mkdir(parents=True, exist_ok=True)

        for f in data["raw_files"]:
            shutil.copy2(f, target / f.name)

        print(f"[RAW] {mat} → {len(data['raw_files'])} files")

# -------------------------
# SAVE CUSTOM
# -------------------------

def save_custom():

    for mat, data in materials.items():

        if not data["custom_files"]:
            continue

        target = CUSTOM_DIR / mat
        target.mkdir(parents=True, exist_ok=True)

        for f in data["custom_files"]:
            shutil.copy2(f, target / f.name)

        # processo custom
        desc = ask(f"Describe CUSTOM process for {mat} (or leave empty)")

        if desc:
            process_data = interpret_process(desc)

            with open(target / "process.json", "w", encoding="utf-8") as fp:
                json.dump(process_data, fp, indent=2)

        print(f"[CUSTOM] {mat} → {len(data['custom_files'])} files")

# -------------------------
# MAIN
# -------------------------

def run_importer():

    if not TEMP_DIR.exists():
        print("Missing temp/import_batch")
        return

    files = [f for f in TEMP_DIR.iterdir() if f.suffix.lower() in VALID_EXT]

    if not files:
        print("No valid files")
        return

    print(f"\nFILES FOUND: {len(files)}")

    process_files(files)

    print("\n--- SAVING RAW ---")
    save_raw()

    print("\n--- SAVING CUSTOM ---")
    save_custom()

    print("\nIMPORT COMPLETE")

# -------------------------
# ENTRY
# -------------------------

if __name__ == "__main__":
    run_importer()