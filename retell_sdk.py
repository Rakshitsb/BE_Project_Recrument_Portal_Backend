"""Compatibility wrapper for the installed Retell SDK.

This project already has a local ``retell`` package, so importing
``from retell import Retell`` would resolve to the app package instead of the
installed SDK. Load the SDK directly from site-packages instead.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_retell_class():
    project_root = Path(__file__).resolve().parent

    for entry in sys.path:
        if not entry:
            continue

        entry_path = Path(entry).resolve()

        # Skip only the repository root itself so we don't pick up the local
        # app package named `retell`. Do not skip nested virtualenv paths such
        # as `/opt/render/project/src/.venv/.../site-packages`.
        try:
            if entry_path == project_root:
                continue
        except Exception:
            continue

        sdk_init = entry_path / "retell" / "__init__.py"
        if not sdk_init.exists():
            continue

        spec = importlib.util.spec_from_file_location(
            "retell_sdk_external",
            sdk_init,
            submodule_search_locations=[str(sdk_init.parent)],
        )
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        retell_class = getattr(module, "Retell", None)
        if retell_class is not None:
            return retell_class

    raise ImportError("Installed Retell SDK not found in site-packages")


Retell = _load_retell_class()

__all__ = ["Retell"]
