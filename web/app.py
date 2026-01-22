# app.py
# Entry point for the Backlogia web application

import os
import sys

# Allow running as script or module
if __name__ == "__main__":
    # Add parent directory to path when running as script
    sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", debug=debug, port=port)
