from typing import Literal
from ..resources import (
    pokedex_path,
    pokedesc_lang_path,
    pokenames_lang_path,
    learnset_path,
    moves_file_path,
    poke_evo_path,
    poke_species_path,
    csv_file_items_cost,
    stats_csv,
    pokemon_csv,
)
from aqt.utils import showWarning
from aqt import mw
import json
import random
import csv
from ..pyobj.error_handler import show_warning_with_traceback

GROWTH_RATES = {
    1: "slow",
    2: "medium",
    3: "fast",
    4: "medium-slow",
    5: "slow-then-very-fast",
    6: "fast-then-very-slow"
}

STATS = {
    1: "hp",
    2: "attack",
    3: "defense",
    4: "special-attack",
    5: "special-defense",
    6: "speed",
}

# === CACHE SINGLETONS ===
_pokedex_cache = None
_pokedex_id_index = None
_pokemon_csv_cache = None
_stats_csv_cache = None
_poke_species_cache = None
_poke_evo_cache = None
_pokenames_lang_cache = None
_pokedesc_lang_cache = None
_moves_file_cache = None
_items_cost_cache = None

def _load_pokedex_cache():
    global _pokedex_cache
    if _pokedex_cache is None:
        with open(pokedex_path, "r", encoding="utf-8") as file:
            _pokedex_cache = json.load(file)
    return _pokedex_cache

def _load_pokedex_id_index():
    """Build reverse index: species_id/actual_id -> internal_name for O(1) speed"""
    global _pokedex_id_index
    if _pokedex_id_index is None:
        data = _load_pokedex_cache()
        _pokedex_id_index = {}
        for entry_name, attrs in data.items():
            aid = attrs.get("actual_id")
            sid = attrs.get("species_id")
            if aid: _pokedex_id_index[int(aid)] = entry_name
            if sid and sid not in _pokedex_id_index: _pokedex_id_index[int(sid)] = entry_name
    return _pokedex_id_index

def _load_pokemon_csv_cache():
    global _pokemon_csv_cache
    if _pokemon_csv_cache is None:
        _pokemon_csv_cache = {}
        with open(pokemon_csv, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                _pokemon_csv_cache[int(row["id"])] = row
    return _pokemon_csv_cache

def _load_stats_csv_cache():
    global _stats_csv_cache
    if _stats_csv_cache is None:
        _stats_csv_cache = {}
        with open(stats_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = int(row["pokemon_id"])
                if pid not in _stats_csv_cache: _stats_csv_cache[pid] = {}
                _stats_csv_cache[pid][int(row["stat_id"])] = int(row["effort"])
    return _stats_csv_cache

def _load_poke_species_cache():
    global _poke_species_cache
    if _poke_species_cache is None:
        _poke_species_cache = {}
        with open(poke_species_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                _poke_species_cache[int(row["id"])] = row
    return _poke_species_cache

def _load_poke_evo_cache():
    global _poke_evo_cache
    if _poke_evo_cache is None:
        _poke_evo_cache = []
        with open(poke_evo_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file, delimiter="\t")
            for row in reader:
                _poke_evo_cache.append(row)
    return _poke_evo_cache

def _load_pokenames_lang_cache():
    global _pokenames_lang_cache
    if _pokenames_lang_cache is None:
        _pokenames_lang_cache = []
        with open(pokenames_lang_path, mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                _pokenames_lang_cache.append(row)
    return _pokenames_lang_cache

def _load_pokedesc_lang_cache():
    global _pokedesc_lang_cache
    if _pokedesc_lang_cache is None:
        _pokedesc_lang_cache = []
        with open(pokedesc_lang_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                _pokedesc_lang_cache.append(row)
    return _pokedesc_lang_cache

def _load_moves_file_cache():
    global _moves_file_cache
    if _moves_file_cache is None:
        with open(moves_file_path, "r", encoding="utf-8") as file:
            _moves_file_cache = json.load(file)
    return _moves_file_cache

def _load_items_cost_cache():
    global _items_cost_cache
    if _items_cost_cache is None:
        _items_cost_cache = []
        with open(csv_file_items_cost, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                _items_cost_cache.append(row)
    return _items_cost_cache

def _normalize_language_id(language):
    """Map unsupported language IDs to a fallback that exists in data files."""
    try:
        lang = int(language)
    except Exception:
        return 9  # default to English on any parsing issue
    if lang == 14:  # Spanish (LatAm) falls back to Spanish data
        return 7
    return lang


def special_pokemon_names_for_min_level(name):
    if name == "flabébé":
        return "flabebe"
    elif name == "sirfetch'd":
        return "sirfetchd"
    elif name == "farfetch'd":
        return "farfetchd"
    elif name == "porygon-z":
        return "porygonz"
    elif name == "kommo-o":
        return "kommoo"
    elif name == "hakamo-o":
        return "hakamoo"
    elif name == "jangmo-o":
        return "jangmoo"
    elif name == "mr. rime":
        return "mrrime"
    elif name == "mr. mime":
        return "mrmime"
    elif name == "mime jr.":
        return "mimejr"
    elif name == "nidoran♂":
        return "nidoranm"
    elif name == "nidoran":
        return "nidoranf"
    elif name == "keldeo[e]":
        return "keldeo"
    elif name == "mew[e]":
        return "mew"
    elif name == "deoxys[e]":
        return "deoxys"
    elif name == "jirachi[e]":
        return "jirachi"
    elif name == "arceus[e]":
        return "arceus"
    elif name == "shaymin[e]":
        return "shaymin-land"
    elif name == "darkrai [e]":
        return "darkrai"
    elif name == "manaphy[e]":
        return "manaphy"
    elif name == "phione[e]":
        return "phione"
    elif name == "celebi[e]":
        return "celebi"
    elif name == "magearna[e]":
        return "magearna"
    elif name == "type: null" or name == "type-null":
        return "typenull"
    elif name == "ho-oh":
        return "hooh"
    elif name == "tapu-koko":
        return "tapukoko"
    elif name == "tapu-lele":
        return "tapulele"
    elif name == "tapu-bulu":
        return "tapubulu"
    elif name == "tapu-fini":
        return "tapufini"
    elif name == "ting-lu":
        return "tinglu"
    elif name == "chien-pao":
        return "chienpao"
    elif name == "wo-chien":
        return "wochien"
    elif name == "chi-yu":
        return "chiyu"
    else:
        return name


def search_pokedex(pokemon_name, variable):
    try:
        pokemon_name = special_pokemon_names_for_min_level(pokemon_name)
        pokedex_data = _load_pokedex_cache()

        # Create a copy of the name to modify
        current_name = pokemon_name

        while True:
            # 1. Try to find a match with the current name
            if current_name in pokedex_data:
                pokemon_info = pokedex_data[current_name]
                var = pokemon_info.get(variable)
                if var is not None:
                    return var

            # 2. If no match, find the last hyphen
            last_hyphen_index = current_name.rfind("-")

            # 3. If no hyphen is found, we can't shorten the name anymore.
            if last_hyphen_index == -1:
                break

            # 4. Remove the suffix and try again in the next iteration
            current_name = current_name[:last_hyphen_index]

        # 5. If no match was ever found, return an empty list
        return []

    except Exception as e:
        show_warning_with_traceback(
            parent=mw,
            exception=e,
            message=f"Error searching for pokemon '{pokemon_name}'",
        )
        return []

def search_pokedex_by_id(species_id):
    index = _load_pokedex_id_index()
    return index.get(int(species_id), "Pokémon not found")


def get_mainpokemon_evo(pokemon_name):
    pokedex_data = _load_pokedex_cache()
    if pokemon_name not in pokedex_data:
        return []
    pokemon_info = pokedex_data[pokemon_name]
    evolutions = pokemon_info.get("evos", [])
    return evolutions

def get_growth_rate(species_id: int) -> str:
    cache = _load_poke_species_cache()
    row = cache.get(int(species_id))
    if row:
        return GROWTH_RATES[int(row["growth_rate_id"])]
    raise ValueError(species_id)

def get_base_experience(actual_id: int) -> int:
    cache = _load_pokemon_csv_cache()
    row = cache.get(int(actual_id))
    if row:
        return int(row["base_experience"])
    raise ValueError(actual_id)

def get_effort_values(actual_id: int) -> dict[str, int]:
    cache = _load_stats_csv_cache()
    evs = cache.get(int(actual_id), {})
    
    return {
        "hp": evs.get(1, 0),
        "attack": evs.get(2, 0),
        "defense": evs.get(3, 0),
        "special-attack": evs.get(4, 0),
        "special-defense": evs.get(5, 0),
        "speed": evs.get(6, 0),
    }

def get_pokemon_descriptions(species_id, language):
    descriptions = []
    language = _normalize_language_id(language)
    cache = _load_pokedesc_lang_cache()
    for row in cache:
        if (
            int(row["species_id"]) == species_id
            and int(row["language_id"]) == language
        ):
            flavor_text = row["flavor_text"].replace("\x0c", " ")
            descriptions.append(flavor_text)
            
    if descriptions:
        return random.choice(descriptions)
    return "Description not found."


def get_pokemon_diff_lang_name(pokemon_id: int, language: int):
    language = _normalize_language_id(language)
    cache = _load_pokenames_lang_cache()
    for row in cache:
        species_id, lang_id, name, genus = row
        if int(species_id) == pokemon_id and int(lang_id) == language:
            return name
    return "No Translation in this language"


def extract_ids_from_file():
    try:
        # get_all_pokemon_ids returns a set of integer IDs natively from SQLite virtual columns
        ids = mw.ankimon_db.get_all_pokemon_ids()
        return sorted(list(ids))
    except Exception as e:
        show_warning_with_traceback(
            parent=mw, exception=e, message="Error extracting IDs from file"
        )
        return []


from .learnset_retrieval import get_all_pokemon_moves  # noqa: F401 — re-export for backwards compat


def find_details_move(move_name: str) -> dict:
    try:
        moves_data = _load_moves_file_cache()
        move = moves_data.get(move_name.lower())
        if move:
            return move
        move_name = move_name.replace(" ", "")
        move = moves_data.get(move_name.lower())
        if move:
            return move
        move_name = move_name.replace("-", "")
        move = moves_data.get(move_name.lower())
        if move:
            return move
        else:
            move = moves_data.get("tackle")
            showWarning(f"Move '{move_name}' not found. Returning default move 'tackle'.")
            return move
                
    except Exception as e:
        show_warning_with_traceback(
            parent=mw,
            exception=e,
            message=f"There is an issue in find_details_move for move: {move_name}. Returning to default move 'tackle'."
        )
        return _load_moves_file_cache().get("tackle")


def get_pokemon_evolution_data_all(pokemon_id):
    cache = _load_poke_evo_cache()
    for row in cache:
        if int(row["id"]) == pokemon_id:
            evolution_data = {
                "id": row["id"],
                "evolved_species_id": row["evolved_species_id"],
                "evolution_trigger_id": row["evolution_trigger_id"],
                "trigger_item_id": row["trigger_item_id"],
                "minimum_level": row["minimum_level"],
                "gender_id": row["gender_id"],
                "location_id": row["location_id"],
                "held_item_id": row["held_item_id"],
                "time_of_day": row["time_of_day"],
                "known_move_id": row["known_move_id"],
                "known_move_type_id": row["known_move_type_id"],
                "minimum_happiness": row["minimum_happiness"],
                "minimum_beauty": row["minimum_beauty"],
                "minimum_affection": row["minimum_affection"],
                "relative_physical_stats": row["relative_physical_stats"],
                "party_species_id": row["party_species_id"],
                "party_type_id": row["party_type_id"],
                "trade_species_id": row["trade_species_id"],
                "needs_overworld_rain": row["needs_overworld_rain"],
                "turn_upside_down": row["turn_upside_down"],
            }
            return evolution_data
    return None


def check_evolution_by_item(pokemon_id, item_id):
    """
    Check if a Pokémon evolves using a specific item.

    Args:
        pokemon_id (int): The ID of the Pokémon.
        item_id (int): The ID of the item.

    Returns:
        bool: True if the Pokémon evolves with the given item, False otherwise.
    """
    # Get the evolution data for the given Pokémon ID
    possible_evos = pokemon_evolves_from_id(
        pokemon_id
    )  # Ensure this returns a list of possible evolutions
    if not possible_evos:
        showWarning("No possible evos found")
        return False

    # Iterate through the possible evolutions
    for evos in possible_evos:
        evo_data = get_pokemon_evolution_data(int(evos))
        if evo_data:
            if int(evo_data["evolution_trigger_id"]) == 3 and int(
                evo_data["trigger_item_id"]
            ) == int(item_id):
                return int(
                    evo_data["evolved_species_id"]
                )  # Return True as soon as a matching evolution is found

    # If no evolution matches the criteria, return False
    return None


# get pokemon name for next evolution from csv species
# get pokemon id from name
# get from pokemon_evolutions.csv with pokemon evo id the evo trigger id and evolution min_level or item_id


def check_evolution_for_pokemon(
    individual_id, pokemon_id, level, evo_window, everstone=False
):
    """
    Check if a Pokémon evolves using a specific item or level condition.

    Args:
        individual_id (int): The ID of the individual Pokémon.
        id (int): A unique identifier for the Pokémon instance.
        pokemon_id (int): The ID of the Pokémon species.
        level (int): The current level of the Pokémon.
        evo_window (object): The evolution window object for displaying evolution information.
        everstone (bool): Whether the Pokémon is holding an Everstone. Defaults to False.

    Returns:
        int | None: The evolution ID if an evolution is found, or None otherwise.
    """
    if not everstone:
        try:
            # Get the evolution data for the given Pokémon ID
            possible_evos = pokemon_evolves_from_id(
                pokemon_id
            )  # Ensure this returns a list of possible evolutions
            if not possible_evos:
                # showWarning("No possible evolutions found")
                return None

            # Check each possible evolution
            for evos in possible_evos:
                evo_data = get_pokemon_evolution_data(int(evos))
                # Only handle level-up evolutions (trigger_id == 1)
                if evo_data and int(evo_data.get("evolution_trigger_id", 0)) == 1:
                    min_level_str = evo_data.get("minimum_level", "")
                    # Only proceed if min_level_str represents a valid integer
                    if not min_level_str or not str(min_level_str).isdigit():
                        continue  # Skip this evolution if minimum_level is missing or not a number
                    min_level = int(min_level_str)
                    if min_level <= level:
                        evo_window.ask_pokemon_evo(
                            individual_id, pokemon_id, int(evos)
                        )
                        return int(evos)  # Return the evolution ID

            # If no evolutions fit the criteria
            # showWarning("No fitting evolution found for the given level")
            return None
        except Exception as e:
            show_warning_with_traceback(
                parent=mw,
                exception=e,
                message=f"Error checking evolution for Pokémon ID {pokemon_id}",
            )
            return None
    else:
        return None


def check_if_evolution_exists(pokemon_id):
    possible_evos = pokemon_evolves_from_id(
        pokemon_id
    )  # Ensure this returns a list of possible evolutions
    if not possible_evos:
        showWarning("No possible evos found")
        return False
    else:
        return possible_evos


def pokemon_evolves_from_id(pokemon_id):
    evolves_from_ids = []
    try:
        cache = _load_poke_species_cache()
        for species_id, row in cache.items():
            evolves_from_species_id = row.get("evolves_from_species_id")
            if evolves_from_species_id:
                try:
                    if int(evolves_from_species_id) == int(pokemon_id):
                        evolves_from_ids.append(row["id"])
                except ValueError:
                    continue
        return evolves_from_ids
    except Exception as e:
        show_warning_with_traceback(
            exception=e,
            message=f"Error in pokemon_evolves_from_id function: {e} with pokemon_id {pokemon_id}",
        )
        return []


def get_pokemon_evolution_data(pokemon_id):
    cache = _load_poke_evo_cache()
    for row in cache:
        try:
            if int(row["evolved_species_id"]) == int(pokemon_id):
                return row
        except ValueError:
            continue
    return None


def check_key_in_table(column_name, value, file_path):
    # This is a generic helper that still takes file_path, but we should ideally use caches.
    # For now, let's just make it not crash if called.
    try:
        with open(file_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row.get(column_name) and str(row[column_name]) == str(value):
                    return row
    except Exception:
        pass
    return None


def return_name_for_id(pokemon_id):
    cache = _load_pokemon_csv_cache()
    row = cache.get(int(pokemon_id))
    if row:
        return row["identifier"]
    return None


def return_id_for_item_name(item_name):
    cache = _load_items_cost_cache()
    for row in cache:
        if row["identifier"] == item_name:
            return row["id"]
    return None
