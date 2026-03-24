import json
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

# Find the actual learnsets.json file in the user_files directory
_src = Path(__file__).parent.parent / "src"
actual_learnset_path = _src / "Ankimon" / "user_files" / "data_files" / "learnsets.json"

# Load the data once for the test
with open(actual_learnset_path, "r", encoding="utf-8") as file:
    LEARNSETS_DATA = json.load(file)

# Stub resources module with the actual learnset_path
_resources = types.ModuleType("Ankimon.resources")
_resources.learnset_path = str(actual_learnset_path)
sys.modules["Ankimon.resources"] = _resources

# Now load learnset_retrieval from its file
_spec = importlib.util.spec_from_file_location(
    "Ankimon.functions.learnset_retrieval",
    _src / "Ankimon" / "functions" / "learnset_retrieval.py",
)
_lr = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _lr
_spec.loader.exec_module(_lr)

from Ankimon.functions.learnset_retrieval import _get_learnset_moves

def test_all_pokemon_learnsets_are_valid():
    """
    Test that retrieving learnsets for all Pokemon in learnsets.json
    does not throw any ValueError due to malformed level strings.
    """
    pokemon_names = list(LEARNSETS_DATA.keys())

    # We patch json.load to return the pre-loaded dictionary, preventing slow I/O parsing repeatedly.
    with patch("Ankimon.functions.learnset_retrieval.json.load", return_value=LEARNSETS_DATA):
        # Iterate over all Pokemon and all generations to ensure no exceptions are raised
        for pokemon_name in pokemon_names:
            for gen in range(1, 10):
                try:
                    # Level 100 ensures we try to parse as many valid levels as possible
                    _get_learnset_moves(pokemon_name, 100, generation=gen)
                except ValueError as e:
                    pytest.fail(f"ValueError raised for pokemon {pokemon_name} in gen {gen}: {e}")
                except Exception as e:
                    pytest.fail(f"Unexpected exception for pokemon {pokemon_name} in gen {gen}: {e}")
