"""
Allows running RIZYEE with: python -m rizyee
This file just calls main() from rizyee.main.
"""

import sys
from rizyee.main import main
from rizyee.utils.logger import get_logger

logger = get_logger("main")

try:
    main()
except KeyboardInterrupt:
    print("\n")
    logger.info("RIZYEE shutting down. Goodbye, Shiva!")
    sys.exit(0)
