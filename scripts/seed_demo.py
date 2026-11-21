"""Creates a 41-item synthetic wardrobe so you can try the whole app with no photos and no API key."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from fashion import demo, trends, db  # noqa: E402

c = db.conn()
print(f"seeded {demo.seed_demo(c)} demo items")
trends.seed(c)
