"""
Normalizare AI (Llama 3.2) + reguli deterministe pe datele din realtime_experiment/outputs/raw_web/.
Echivalent cu reparator.py din radacina proiectului.

Ruleaza dupa cleanup_realtime.py si inainte de refix_realtime.py.

Utilizare:
    cd realtime_experiment
    python refine_realtime.py
"""

import sys
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# --- Paths locale ---
BASE_DIR    = Path(__file__).parent
RAW_DIR     = BASE_DIR / "outputs" / "raw_web"
REFINED_DIR = BASE_DIR / "outputs" / "refined"
REFINED_DIR.mkdir(parents=True, exist_ok=True)

PARENT_DIR = BASE_DIR.parent
sys.path.insert(0, str(PARENT_DIR))

import reparator  # noqa: E402


# ─── Normalizare AI + reguli deterministe ─────────────────────────────────────

def apply_normalization(files: list[Path]) -> None:
    reparator.OUTPUT_DIR = REFINED_DIR
    for fpath in files:
        log.info("Normalizare: %s", fpath.name)
        reparator.process_file(fpath)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    files = sorted(RAW_DIR.glob("data_*.json"))
    if not files:
        log.warning("Niciun fisier data_*.json gasit in %s. Ruleaza mai intai cleanup_realtime.py.", RAW_DIR)
        return

    log.info("Normalizare AI + reguli deterministe (%d fisiere)...", len(files))
    apply_normalization(files)

    log.info(" Gata! Datele rafinate sunt in: %s", REFINED_DIR)
    log.info("   Ruleaza acum refix_realtime.py.")


if __name__ == "__main__":
    main()
