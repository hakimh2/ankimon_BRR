import json
from typing import Optional

from ..functions.pokedex_functions import search_pokedex, search_pokedex_by_id
from ..resources import mainpokemon_path
from ..pyobj.pokemon_obj import PokemonObject

# default values to fall back in case of load error
MAIN_POKEMON_DEFAULT = {
    "name": "RESTART ANKI",
    "gender": None,
    "level": 5,
    "id": None,
    "ability": None,
    "type": None,
    "base_stats": None,
    "xp": None,
    "ev": None,
    "iv": None,
    "attacks": None,
    "base_experience": None,
    "hp": 100,
    "growth_rate": None,
    "individual_id": None,
    "tier": None,
    "shiny": None,
    "captured_date": None
}


def update_main_pokemon(main_pokemon: Optional[PokemonObject] = None):
    """
    Updates or initializes the main Pokémon object using data from the database.
    Falls back to JSON file for backwards compatibility.
    """
    from ..pyobj.database_manager import get_db
    db = get_db()

    if main_pokemon is None:
        main_pokemon = PokemonObject(**MAIN_POKEMON_DEFAULT)

    mainpokemon_empty = True
    
    # Try database first
    if db.is_migrated():
        main_pokemon_data = db.get_main_pokemon()
        if main_pokemon_data:
            mainpokemon_empty = False
            pokemon_name = search_pokedex_by_id(main_pokemon_data["id"])
            main_pokemon_data["base_stats"] = search_pokedex(pokemon_name, "baseStats")
            if "stats" in main_pokemon_data:
                del main_pokemon_data["stats"]
            main_pokemon.update_stats(**main_pokemon_data)
            
            max_hp = main_pokemon.calculate_max_hp()
            main_pokemon.max_hp = max_hp
            if main_pokemon_data.get("current_hp", max_hp) > max_hp:
                main_pokemon_data["current_hp"] = max_hp
            main_pokemon.hp = main_pokemon_data.get("current_hp", max_hp)
            return main_pokemon, mainpokemon_empty
        else:
            return PokemonObject(**MAIN_POKEMON_DEFAULT), mainpokemon_empty
    
    # Fallback to JSON for backwards compatibility
    if mainpokemon_path.is_file():
        with open(mainpokemon_path, "r", encoding="utf-8") as mainpokemon_json:
            try:
                main_pokemon_data = json.load(mainpokemon_json)
                if main_pokemon_data:
                    mainpokemon_empty = False
                    pokemon_name = search_pokedex_by_id(main_pokemon_data[0]["id"])
                    main_pokemon_data[0]["base_stats"] = search_pokedex(pokemon_name, "baseStats")
                    if "stats" in main_pokemon_data[0]:
                        del main_pokemon_data[0]["stats"]
                    main_pokemon.update_stats(**main_pokemon_data[0])
                    save_main_pokemon(main_pokemon)
                else:
                    main_pokemon = PokemonObject(**MAIN_POKEMON_DEFAULT)
                max_hp = main_pokemon.calculate_max_hp()
                main_pokemon.max_hp = max_hp
                if main_pokemon_data[0].get("current_hp", max_hp) > max_hp:
                    main_pokemon_data[0]["current_hp"] = max_hp
                if main_pokemon_data:
                    main_pokemon.hp = main_pokemon_data[0].get("current_hp", max_hp)
                return main_pokemon, mainpokemon_empty
            except Exception:
                main_pokemon = PokemonObject(**MAIN_POKEMON_DEFAULT)
                return main_pokemon, mainpokemon_empty
    else:
        return PokemonObject(**MAIN_POKEMON_DEFAULT), mainpokemon_empty


def save_main_pokemon(main_pokemon: PokemonObject):
    """Saves the main Pokémon object to the database."""
    from ..pyobj.database_manager import get_db
    db = get_db()
    
    if hasattr(main_pokemon, 'to_dict'):
        data = main_pokemon.to_dict()
    else:
        data = main_pokemon.__dict__
    
    db.save_main_pokemon(data)
