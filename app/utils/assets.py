from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict, cast


class ViteManifestEntry(TypedDict, total=False):
    file: str
    css: list[str]


class ViteAssetBundle(TypedDict):
    js: str
    css: list[str]


def _manifest_candidates(base_dir: str) -> tuple[Path, ...]:
    root = Path(base_dir)
    return (
        root / "static" / "dist" / ".vite" / "manifest.json",
        root / "static" / "dist" / "manifest.json",
    )


def _load_manifest(base_dir: str) -> dict[str, ViteManifestEntry]:
    for manifest_path in _manifest_candidates(base_dir):
        if manifest_path.exists():
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            return cast(dict[str, ViteManifestEntry], raw)
    raise FileNotFoundError("Vite manifest not found. Run `npm run build` in frontend/.")


def _resolve_entry(manifest: dict[str, ViteManifestEntry], entry: str) -> ViteManifestEntry:
    candidates = (entry, entry.lstrip("/"), entry.removeprefix("frontend/"))
    for key in candidates:
        if key in manifest:
            return manifest[key]

    available = ", ".join(sorted(manifest.keys())[:10])
    raise KeyError(f"Vite entry '{entry}' not found in manifest. Available entries: {available}")


def vite_assets(entry: str, base_dir: str) -> ViteAssetBundle:
    manifest = _load_manifest(base_dir)
    item = _resolve_entry(manifest, entry)

    js_file = item.get("file")
    if not js_file:
        raise KeyError(f"Manifest entry '{entry}' does not contain a JS file.")

    css_files = item.get("css", [])
    return {
        "js": f"/static/dist/{js_file}",
        "css": [f"/static/dist/{css_file}" for css_file in css_files],
    }
