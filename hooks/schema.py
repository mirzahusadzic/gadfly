"""MkDocs hook: publish the frame's JSON Schema at the address its $id names
(the site root), from the one copy the package ships."""

import shutil
from pathlib import Path

SCHEMA = Path(__file__).parent.parent / "gadfly" / "frame.schema.json"


def on_post_build(config):
    shutil.copyfile(SCHEMA, Path(config["site_dir"]) / SCHEMA.name)
