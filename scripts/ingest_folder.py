"""Usage: python scripts/ingest_folder.py path/to/photos  (clothing and jewellery only, no faces)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fashion import vectors, pipeline, config  # noqa: E402

config.ensure_dirs()
store = vectors.QdrantStore()
files = [p for p in Path(sys.argv[1]).iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}]
for i, p in enumerate(sorted(files), 1):
    try:
        print(f"[{i}/{len(files)}] {p.name} -> {pipeline.ingest_image(p, store)}")
    except Exception as e:  # keep going; failures are visible, not silent
        print(f"[{i}/{len(files)}] {p.name} FAILED: {e}")
