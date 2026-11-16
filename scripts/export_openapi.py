"""Write the Mosaic API OpenAPI schema to contracts/. CI fails if the committed copy is stale."""

import json
from pathlib import Path

from mosaic_api import create_app

OUT = Path(__file__).resolve().parent.parent / "contracts" / "mosaic-api.openapi.json"


def main() -> None:
    schema = create_app().openapi()
    OUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"wrote {OUT.relative_to(Path.cwd()) if OUT.is_relative_to(Path.cwd()) else OUT}")


if __name__ == "__main__":
    main()
