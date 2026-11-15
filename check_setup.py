import sys
import importlib

print("Python:", sys.version.split()[0])
for name in ("pandas", "numpy", "faker"):
    try:
        mod = importlib.import_module(name)
        print(f"  {name}: OK ({getattr(mod, '__version__', 'installed')})")
    except ImportError:
        print(f"  {name}: MISSING -> run: pip install -r requirements.txt")

import config
total = sum(config.COUNTRY_WEIGHTS.values())
print("config.py loaded. Country weights sum to", round(total, 3), "(must be 1.0)")
print("Time window:", config.START_DATE, "to", config.END_DATE)