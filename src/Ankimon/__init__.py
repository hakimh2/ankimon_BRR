# -*- coding: utf-8 -*-

# Ankimon
# Copyright (C) 2024 Unlucky-Life

# This program is free software: you can redistribute it and/or modify
# by the Free Software Foundation
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# Important - If you redistribute it and/or modify this addon - must give contribution in Title and Code
# aswell as ask for permission to modify / redistribute this addon or the code itself

try:
    from .debug_console import show_ankimon_dev_console
except ModuleNotFoundError:
    # Debug console should not be available to non devs, so it's fine if this import doesn't succeed
    pass

import json
import random
import copy
from typing import Union

import aqt
from anki.hooks import addHook, wrap
from aqt import gui_hooks, mw, utils
from aqt.qt import QDialog
from aqt.operations import QueryOp
from aqt.reviewer import Reviewer
from aqt.utils import downArrow, showWarning, tr, tooltip
from PyQt6.QtWidgets import QDialog
from aqt.gui_hooks import webview_will_set_content
from aqt.webview import WebContent
import markdown

from .resources import ensure_ankimon_infrastructure, user_path, IS_EXPERIMENTAL_BUILD, addon_ver, addon_dir
ensure_ankimon_infrastructure(addon_dir, user_path)

from .singletons import settings_obj

no_more_news = settings_obj.get("misc.YouShallNotPass_Ankimon_News")
ssh = settings_obj.get("misc.ssh")
defeat_shortcut = settings_obj.get(
    "controls.defeat_key"
)  # default: 5; ; Else if not 5 => controll + Key for capture
catch_shortcut = settings_obj.get(
    "controls.catch_key"
)  # default: 6; Else if not 6 => controll + Key for capture
reviewer_buttons = settings_obj.get(
    "controls.pokemon_buttons"
)  # default: true; false = no pokemon buttons in reviewer

from .resources import (
    addon_dir,
    pkmnimgfolder,
    mypokemon_path,
    mainpokemon_path,
    itembag_path,
    sound_list_path
)
from .menu_buttons import create_menu_actions
from .hooks import setupHooks
from .texts import _bottomHTML_template, button_style
from .utils import (
    check_folders_exist,
    safe_get_random_move,
    test_online_connectivity,
    read_local_file,
    read_github_file,
    compare_files,
    write_local_file,
    count_items_and_rewrite,
    play_effect_sound,
    get_main_pokemon_data,
    play_sound,
    load_collected_pokemon_ids,
)
from .functions.url_functions import (
    open_team_builder,
    rate_addon_url,
    report_bug,
    join_discord_url,
    open_leaderboard_url,
)
from .functions.badges_functions import (
    get_achieved_badges,
    handle_review_count_achievement,
    check_for_badge,
    receive_badge,
)
from .functions.pokemon_showdown_functions import (
    export_to_pkmn_showdown,
    export_all_pkmn_showdown,
    flex_pokemon_collection,
)
from .functions.drawing_utils import tooltipWithColour
from .functions.discord_function import DiscordPresence
from .functions.rate_addon_functions import rate_this_addon
from .functions.encounter_functions import (
    generate_random_pokemon,
    new_pokemon,
    catch_pokemon,
    kill_pokemon,
    handle_enemy_faint,
    handle_main_pokemon_faint,
)
from .gui_entities import UpdateNotificationWindow, CheckFiles
from .pyobj.download_sprites import show_agreement_and_download_dialog
from .pyobj.help_window import HelpWindow
from .pyobj.backup_files import run_backup
from .pyobj.backup_manager import BackupManager
from .pyobj.ankimon_sync import setup_ankimon_sync_hooks, check_and_sync_pokemon_data
from .pyobj.tip_of_the_day import show_tip_of_the_day
from .classes.choose_move_dialog import MoveSelectionDialog
from .poke_engine.ankimon_hooks_to_poke_engine import simulate_battle_with_poke_engine
from .singletons import (
    reviewer_obj,
    logger,
    settings_obj,
    settings_window,
    translator,
    main_pokemon,
    enemy_pokemon,
    trainer_card,
    ankimon_tracker_obj,
    test_window,
    achievement_bag,
    shop_manager,
    ankimon_tracker_window,
    pokedex_window,
    eff_chart,
    gen_id_chart,
    license,
    credits,
    evo_window,
    starter_window,
    item_window,
    version_dialog,
    achievements,
    pokemon_pc,
    ankimon_db,
)

from .pyobj.pokemon_trade import check_and_award_monthly_pokemon

from .functions.battle_functions import (
    update_pokemon_battle_status,
    validate_pokemon_status,
    process_battle_data,
)

from .pyobj.error_handler import show_warning_with_traceback

mw.settings_ankimon = settings_window
mw.logger = logger
mw.translator = translator
mw.settings_obj = settings_obj

from .gui_classes import overview_team

# Log an startup message
logger.log_and_showinfo("game", translator.translate("startup"))
logger.log_and_showinfo("game", translator.translate("backing_up_files"))

# backup_files
try:
    run_backup()
except Exception as e:
    show_warning_with_traceback(parent=mw, exception=e, message="Backup error:")

backup_manager = BackupManager(logger, settings_obj)

# Migrate existing JSON data to SQLite database (one-time operation with dialog)
if not ankimon_db.is_migrated():
    from .pyobj.migration_dialog import show_migration_dialog_if_needed
    from .resources import (
        mypokemon_path, mainpokemon_path, itembag_path, badgebag_path,
        team_pokemon_path, pokemon_history_path, user_path_credentials,
        rate_path
    )
    show_migration_dialog_if_needed(
        ankimon_db, mypokemon_path, mainpokemon_path, itembag_path, badgebag_path, mw,
        team_pokemon_path, pokemon_history_path, user_path_credentials, rate_path
    )

if settings_obj.get("misc.developer_mode"):
    backup_manager.create_backup(manual=False)

# Initialize mutator and mutator_full_reset
global new_state
global mutator_full_reset
global user_hp_after
global opponent_hp_after
global dmg_from_enemy_move
global dmg_from_user_move

# Initialize collected IDs cache
# Call this during addon initialization
collected_pokemon_ids = set()
_collection_loaded = False
if not _collection_loaded:  # If the collection hasn't already been loaded
    collected_pokemon_ids = load_collected_pokemon_ids()
    _collection_loaded = True


with open(sound_list_path, "r", encoding="utf-8") as json_file:
    sound_list = json.load(json_file)

ankimon_tracker_obj.pokemon_encounter = 0

"""
get web exports ready for special reviewer look
"""


# Set up web exports for static files
mw.addonManager.setWebExports(
    __name__, r"user_files/.*\.(css|js|jpg|gif|html|ttf|png|mp3)"
)


def on_webview_will_set_content(web_content: WebContent, context) -> None:
    if not isinstance(context, aqt.reviewer.Reviewer):
        return
    ankimon_package = mw.addonManager.addonFromModule(__name__)
    web_content.js.append(
        f"/_addons/{ankimon_package}/user_files/web/ankimon_hud_portal.js"
    )

webview_will_set_content.append(on_webview_will_set_content)

# check for sprites, data
sound_files = check_folders_exist(pkmnimgfolder, "sounds")
back_sprites = check_folders_exist(pkmnimgfolder, "back_default")
back_default_gif = check_folders_exist(pkmnimgfolder, "back_default_gif")
front_sprites = check_folders_exist(pkmnimgfolder, "front_default")
front_default_gif = check_folders_exist(pkmnimgfolder, "front_default_gif")
item_sprites = check_folders_exist(pkmnimgfolder, "items")
badges_sprites = check_folders_exist(pkmnimgfolder, "badges")

database_complete = all(
    [
        back_sprites,
        front_sprites,
        front_default_gif,
        back_default_gif,
        item_sprites,
        badges_sprites,
    ]
)

if not database_complete:
    show_agreement_and_download_dialog(force_download=True)
    dialog = CheckFiles()
    dialog.show()

sync_dialog = None


# If reviewer showed question; start card_timer for answering card
def on_show_question(Card):
    """
    This function is called when a question is shown.
    You can access and manipulate the card object here.
    """
    ankimon_tracker_obj.start_card_timer()  # This line should have 4 spaces of indentation


def on_show_answer(Card):
    """
    This function is called when a question is shown.
    You can access and manipulate the card object here.
    """
    ankimon_tracker_obj.stop_card_timer()  # This line should have 4 spaces of indentation


def on_reviewer_did_show_question(card):
    reviewer_obj.update_life_bar(mw.reviewer, None, None)


gui_hooks.reviewer_did_show_question.append(on_show_question)
gui_hooks.reviewer_did_show_answer.append(on_show_answer)
gui_hooks.reviewer_did_show_question.append(on_reviewer_did_show_question)

setupHooks(None, ankimon_tracker_obj)

online_connectivity = test_online_connectivity()

from .changelog import check_and_show_changelog, open_help_window
check_and_show_changelog(online_connectivity, ssh, no_more_news)


def answerCard_before(filter, reviewer, card):
    utils.answBtnAmt = reviewer.mw.col.sched.answerButtons(card)
    return filter


# Globale Variable für die Zählung der Bewertungen


def answerCard_after(rev, card, ease):
    maxEase = rev.mw.col.sched.answerButtons(card)
    aw = aqt.mw.app.activeWindow() or aqt.mw
    # Aktualisieren Sie die Zählung basierend auf der Bewertung
    if ease == 1:
        ankimon_tracker_obj.review("again")
    elif ease == maxEase - 2:
        ankimon_tracker_obj.review("hard")
    elif ease == maxEase - 1:
        ankimon_tracker_obj.review("good")
    elif ease == maxEase:
        ankimon_tracker_obj.review("easy")
    else:
        # default behavior for unforeseen cases
        tooltip("Error in ColorConfirmation: Couldn't interpret ease")
    ankimon_tracker_obj.reset_card_timer()


aqt.gui_hooks.reviewer_will_answer_card.append(answerCard_before)
aqt.gui_hooks.reviewer_did_answer_card.append(answerCard_after)


# get main pokemon details:
if database_complete:
    try:
        (
            mainpokemon_name,
            mainpokemon_id,
            mainpokemon_ability,
            mainpokemon_type,
            mainpokemon_stats,
            mainpokemon_attacks,
            mainpokemon_level,
            mainpokemon_base_experience,
            mainpokemon_xp,
            mainpokemon_hp,
            mainpokemon_current_hp,
            mainpokemon_growth_rate,
            mainpokemon_ev,
            mainpokemon_iv,
            mainpokemon_evolutions,
            mainpokemon_battle_stats,
            mainpokemon_gender,
            mainpokemon_nickname,
        ) = get_main_pokemon_data()
        starter = True
    except Exception:
        starter = False
        mainpokemon_level = 5
    # name, id, level, ability, type, stats, enemy_attacks, base_experience, growth_rate, ev, iv, gender, battle_status, battle_stats, tier, ev_yield, shiny = generate_random_pokemon()
    (
        name,
        id,
        level,
        ability,
        type,
        base_stats,
        enemy_attacks,
        base_experience,
        growth_rate,
        ev,
        iv,
        gender,
        battle_status,
        battle_stats,
        tier,
        ev_yield,
        shiny,
    ) = generate_random_pokemon(main_pokemon.level, ankimon_tracker_obj)
    pokemon_data = {
        "name": name,
        "id": id,
        "level": level,
        "ability": ability,
        "type": type,
        "base_stats": base_stats,
        "attacks": enemy_attacks,
        "base_experience": base_experience,
        "growth_rate": growth_rate,
        "ev": ev,
        "iv": iv,
        "gender": gender,
        "battle_status": battle_status,
        "battle_stats": battle_stats,
        "tier": tier,
        "ev_yield": ev_yield,
        "shiny": shiny,
    }
    enemy_pokemon.update_stats(**pokemon_data)
    max_hp = enemy_pokemon.calculate_max_hp()
    enemy_pokemon.current_hp = max_hp
    enemy_pokemon.hp = max_hp
    enemy_pokemon.max_hp = max_hp
    ankimon_tracker_obj.randomize_battle_scene()

from .battle_loop import on_review_card, init_battle_state
init_battle_state(collected_pokemon_ids)
gui_hooks.reviewer_did_answer_card.append(on_review_card)

if database_complete:
    badge_list = get_achieved_badges()
    if len(badge_list) > 1:  # has atleast one badge
        rate_this_addon()

if database_complete:
    # Check if user has any pokemon in database
    from .pyobj.database_manager import get_db
    db = get_db()
    if db.get_pokemon_count() == 0:
        starter_window.display_starter_pokemon()

count_items_and_rewrite()

# buttonlayout
# Create menu actions
# Create menu actions
create_menu_actions(
    database_complete,
    online_connectivity,
    item_window,
    test_window,
    achievement_bag,
    open_team_builder,
    export_to_pkmn_showdown,
    export_all_pkmn_showdown,
    flex_pokemon_collection,
    eff_chart,
    gen_id_chart,
    credits,
    license,
    open_help_window,
    report_bug,
    rate_addon_url,
    version_dialog,
    trainer_card,
    ankimon_tracker_window,
    logger,
    settings_window,
    shop_manager,
    pokedex_window,
    settings_obj.get("controls.key_for_opening_closing_ankimon"),
    join_discord_url,
    open_leaderboard_url,
    settings_obj,
    addon_dir,
    pokemon_pc,
    backup_manager
)

# https://goo.gl/uhAxsg
# https://www.reddit.com/r/PokemonROMhacks/comments/9xgl7j/pokemon_sound_effects_collection_over_3200_sfx/
# https://archive.org/details/pokemon-dp-sound-library-disc-2_202205
# https://www.sounds-resource.com/nintendo_switch/pokemonswordshield/

from .hook_registry import (
    CatchPokemonHook,
    DefeatPokemonHook,
    add_catch_pokemon_hook,
    add_defeat_pokemon_hook,
)


from .profile_hooks import register_profile_hooks
register_profile_hooks(
    online_connectivity,
    backup_manager,
    CatchPokemonHook,
    DefeatPokemonHook,
    add_catch_pokemon_hook,
    add_defeat_pokemon_hook,
    collected_pokemon_ids,
)


from .reviewer_ui import setup_reviewer_ui, set_collected_ids, catch_shortcut_function, defeat_shortcut_function
set_collected_ids(collected_pokemon_ids)
setup_reviewer_ui(catch_shortcut, defeat_shortcut, reviewer_buttons)


from .discord_integration import setup_discord_hooks
setup_discord_hooks()
