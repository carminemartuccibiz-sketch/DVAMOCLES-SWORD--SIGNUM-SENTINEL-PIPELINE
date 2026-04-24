import os
import sys
from pathlib import Path
from PIL import Image

try:
    import win32com.client
except ImportError:
    print("ERRORE: Installa la libreria eseguendo: pip install pywin32")
    sys.exit(1)

def setup_forge_shortcut():
    print("--- DVAMOCLES SWORD: ICON & SHORTCUT FORGE ---")
    
    work_dir = os.path.abspath(".")
    img_path = os.path.join(work_dir, "sss.png")
    ico_path = os.path.join(work_dir, "signum_icon.ico")
    bat_path = os.path.join(work_dir, "start_forge.bat")
    
    # 1. Verifica che i file esistano
    if not os.path.exists(img_path):
        print(f"ERRORE: Immagine non trovata in {img_path}")
        return
    if not os.path.exists(bat_path):
        print(f"ERRORE: File batch non trovato in {bat_path}")
        return

    # 2. Converte l'immagine in formato .ICO (mantenendo la trasparenza e le dimensioni corrette)
    print("1. Forgiatura dell'Icona in corso...")
    try:
        img = Image.open(img_path)
        # Ritaglia un quadrato perfetto al centro se l'immagine non è quadrata
        min_dim = min(img.size)
        left = (img.width - min_dim) / 2
        top = (img.height - min_dim) / 2
        img_cropped = img.crop((left, top, left + min_dim, top + min_dim))
        
        img_cropped.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32)])
        print(f"   Icona generata con successo: {ico_path}")
    except Exception as e:
        print(f"   Errore durante la creazione dell'icona: {e}")
        return

    # 3. Crea il collegamento sul Desktop
    print("2. Creazione dell'accesso rapido sul Desktop...")
    try:
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        shortcut_path = os.path.join(desktop, "DVAMOCLES SWORD.lnk")
        
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = bat_path
        shortcut.WorkingDirectory = work_dir
        shortcut.IconLocation = ico_path
        shortcut.save()
        print(f"   Collegamento creato: {shortcut_path}")
    except Exception as e:
        print(f"   Errore durante la creazione del collegamento: {e}")
        return
        
    print("\nPROCESSO COMPLETATO! Vai sul Desktop e ammira il risultato.")

if __name__ == "__main__":
    setup_forge_shortcut()