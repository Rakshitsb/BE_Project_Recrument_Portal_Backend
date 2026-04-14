import importlib.util
import sys
from pathlib import Path


def _load_retell_class():
    sdk_init = Path(__file__).resolve().parent / "venv" / "Lib" / "site-packages" / "retell" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "retell_sdk_external",
        sdk_init,
        submodule_search_locations=[str(sdk_init.parent)],
    )
    if spec is None or spec.loader is None:
        raise ImportError("Retell SDK not found")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.Retell


Retell = _load_retell_class()
