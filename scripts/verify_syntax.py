import sys
import logging
logging.basicConfig(level=logging.ERROR)

try:
    from src.main import app
    print("Syntax and imports OK")
    sys.exit(0)
except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
