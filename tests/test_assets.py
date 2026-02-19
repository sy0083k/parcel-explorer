import json

import pytest

from app.utils.assets import vite_assets


def test_vite_assets_raises_when_manifest_missing(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        vite_assets("src/map.ts", str(tmp_path))


def test_vite_assets_resolves_entry_from_manifest(tmp_path) -> None:
    manifest_dir = tmp_path / "static" / "dist" / ".vite"
    manifest_dir.mkdir(parents=True)
    manifest = {
        "src/map.ts": {
            "file": "assets/map-abc.js",
            "css": ["assets/map-abc.css"],
        }
    }
    (manifest_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    assets = vite_assets("src/map.ts", str(tmp_path))

    assert assets["js"] == "/static/dist/assets/map-abc.js"
    assert assets["css"] == ["/static/dist/assets/map-abc.css"]
