"""Export FastAPI OpenAPI spec to a JSON file for frontend SDK generation."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.main import app


def main() -> None:
    output = Path(__file__).resolve().parent.parent / "frontend" / "openapi-parse.json"
    spec = app.openapi()
    output.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    print(f"Exported OpenAPI spec to {output}")


if __name__ == "__main__":
    main()
