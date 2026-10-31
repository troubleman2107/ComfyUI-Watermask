"""Load the custom-node root as a package, as ComfyUI's loader does.

Pytest otherwise imports a hyphenated repository's root as bare ``__init__``,
which has no package context for relative imports.
"""
import importlib.util
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    '__init__', root / '__init__.py', submodule_search_locations=[str(root)]
)
package = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = package
spec.loader.exec_module(package)
