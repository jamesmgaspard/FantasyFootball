from pathlib import Path

def ensure_dirs():
    for p in ["data/raw", "data/interim", "data/processed"]:
        Path(p).mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    ensure_dirs()
    print("Data directories are ready.")
