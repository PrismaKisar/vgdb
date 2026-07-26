import sys
from pathlib import Path

# The cover helpers are runnable scripts, not part of the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
