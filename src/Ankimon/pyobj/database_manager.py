"""
AnkimonDB - Consolidated Database Manager for Ankimon

This module provides a SQLite-based storage solution for all Ankimon game data,
replacing multiple JSON files with a single, obfuscated database file.
"""

import base64
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..resources import user_path


class AnkimonDB:
    """Handles all database operations for Ankimon with obfuscation. Currently, the database is obfuscated using a simple XOR cipher."""

    _OBFUSCATION_KEY = "H0tP-!s-N0t-4-C@tG!rL_v2"
    DB_FILENAME = "ankimon.db"

    def __init__(self, logger=None):
        self.logger = logger
        self.db_path = user_path / self.DB_FILENAME
        self._connection: Optional[sqlite3.Connection] = None
        self._setup_database()

    def _log(self, level: str, message: str):
        """Helper for logging."""
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

    # --- Connection Management ---

    def _get_connection(self) -> sqlite3.Connection:
        """Gets or creates a database connection."""
        if self._connection is None:
            self._connection = sqlite3.connect(str(self.db_path))
            self._connection.row_factory = sqlite3.Row  # Access columns by name
        return self._connection

    def close(self):
        """Closes the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    # --- Obfuscation / De-obfuscation ---

    def _obfuscate(self, data: Any) -> str:
        """Obfuscates a Python object to a base64 string using a simple XOR cipher."""
        json_str = json.dumps(data, ensure_ascii=False)
        data_bytes = json_str.encode('utf-8')
        key_bytes = self._OBFUSCATION_KEY.encode('utf-8')
        obfuscated_bytes = bytearray()
        for i, byte in enumerate(data_bytes):
            obfuscated_bytes.append(byte ^ key_bytes[i % len(key_bytes)])
        return base64.b64encode(obfuscated_bytes).decode('utf-8')

    def _deobfuscate(self, obfuscated_str: str) -> Optional[Any]:
        """De-obfuscates a base64 string back to a Python object using a simple XOR cipher."""
        try:
            obfuscated_bytes = base64.b64decode(obfuscated_str)
            key_bytes = self._OBFUSCATION_KEY.encode('utf-8')
            deobfuscated_bytes = bytearray()
            for i, byte in enumerate(obfuscated_bytes):
                deobfuscated_bytes.append(byte ^ key_bytes[i % len(key_bytes)])
            return json.loads(deobfuscated_bytes.decode('utf-8'))
        except Exception as e:
            self._log("error", f"Failed to deobfuscate data: {e}")
            return None

    # --- Database Setup ---

    def _setup_database(self):
        """Creates all necessary tables if they don't exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Table for captured pokemon (replaces mypokemon.json AND mainpokemon.json)
        # is_main flag: 0 = not main, 1 = main pokemon
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS captured_pokemon (
                individual_id TEXT PRIMARY KEY,
                is_main INTEGER DEFAULT 0,
                data TEXT NOT NULL
            )
        """)

        # Check if is_main column exists (for migration from old schema)
        cursor.execute("PRAGMA table_info(captured_pokemon)")
        columns = [row[1] for row in cursor.fetchall()]
        if "is_main" not in columns:
            self._log("info", "Migrating schema: adding is_main column...")
            cursor.execute("ALTER TABLE captured_pokemon ADD COLUMN is_main INTEGER DEFAULT 0")
            # Migrate data from old main_pokemon table if it exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='main_pokemon'")
            if cursor.fetchone():
                cursor.execute("SELECT individual_id, data FROM main_pokemon WHERE id = 1")
                row = cursor.fetchone()
                if row:
                    main_id = row[0]
                    main_data = row[1]
                    # Update the existing pokemon to be main, or insert if not exists
                    cursor.execute(
                        "INSERT OR REPLACE INTO captured_pokemon (individual_id, is_main, data) VALUES (?, 1, ?)",
                        (main_id, main_data)
                    )
                cursor.execute("DROP TABLE main_pokemon")
                self._log("info", "Migrated main_pokemon table to is_main flag")

        # Table for items (replaces items.json)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS items (
                item_name TEXT PRIMARY KEY,
                quantity INTEGER DEFAULT 0,
                data TEXT
            )
        """)

        # Table for badges (replaces badges.json)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS badges (
                badge_id TEXT PRIMARY KEY,
                data TEXT NOT NULL
            )
        """)

        # Metadata table for tracking migration status, etc.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        conn.commit()
        self._log("info", "AnkimonDB: Database schema initialized.")

    # --- Captured Pokemon Operations ---

    def save_pokemon(self, pokemon_data: Dict[str, Any]):
        """Saves or updates a captured pokemon. Preserves is_main flag if pokemon already exists."""
        individual_id = pokemon_data.get("individual_id")
        if not individual_id:
            self._log("error", "Cannot save pokemon without individual_id")
            return False

        obfuscated_data = self._obfuscate(pokemon_data)
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if pokemon already exists to preserve is_main flag
        cursor.execute("SELECT is_main FROM captured_pokemon WHERE individual_id = ?", (individual_id,))
        row = cursor.fetchone()
        
        if row:
            # Update existing - preserve is_main
            cursor.execute(
                "UPDATE captured_pokemon SET data = ? WHERE individual_id = ?",
                (obfuscated_data, individual_id)
            )
        else:
            # Insert new with is_main = 0
            cursor.execute(
                "INSERT INTO captured_pokemon (individual_id, is_main, data) VALUES (?, 0, ?)",
                (individual_id, obfuscated_data)
            )
        conn.commit()
        return True

    def get_pokemon(self, individual_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific pokemon by its individual_id."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT data FROM captured_pokemon WHERE individual_id = ?",
            (individual_id,)
        )
        row = cursor.fetchone()
        if row:
            return self._deobfuscate(row["data"])
        return None

    def get_all_pokemon(self) -> List[Dict[str, Any]]:
        """Retrieves all captured pokemon."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM captured_pokemon")
        results = []
        for row in cursor.fetchall():
            pokemon = self._deobfuscate(row["data"])
            if pokemon:
                results.append(pokemon)
        return results

    def delete_pokemon(self, individual_id: str) -> bool:
        """Deletes a pokemon from the captured collection."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM captured_pokemon WHERE individual_id = ?",
            (individual_id,)
        )
        conn.commit()
        return cursor.rowcount > 0

    def get_pokemon_count(self) -> int:
        """Returns the count of captured pokemon."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM captured_pokemon")
        return cursor.fetchone()[0]

    def get_all_pokemon_ids(self) -> set:
        """Returns a set of all captured pokemon's pokedex IDs."""
        pokemon_list = self.get_all_pokemon()
        return {p.get("id") for p in pokemon_list if p.get("id")}

    # --- Main Pokemon Operations ---

    def save_main_pokemon(self, pokemon_data: Dict[str, Any]):
        """Saves/updates the main pokemon. Sets is_main=1 on this pokemon, is_main=0 on all others."""
        individual_id = pokemon_data.get("individual_id")
        if not individual_id:
            self._log("error", "Cannot save main pokemon without individual_id")
            return False

        obfuscated_data = self._obfuscate(pokemon_data)
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Clear the main flag from all pokemon first
        cursor.execute("UPDATE captured_pokemon SET is_main = 0 WHERE is_main = 1")
        
        # Save/update this pokemon and set as main
        cursor.execute(
            "INSERT OR REPLACE INTO captured_pokemon (individual_id, is_main, data) VALUES (?, 1, ?)",
            (individual_id, obfuscated_data)
        )
        conn.commit()
        return True

    def get_main_pokemon(self) -> Optional[Dict[str, Any]]:
        """Retrieves the main pokemon (the one with is_main=1)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM captured_pokemon WHERE is_main = 1")
        row = cursor.fetchone()
        if row:
            return self._deobfuscate(row["data"])
        return None

    def set_main_pokemon(self, individual_id: str) -> bool:
        """Sets a pokemon as the main pokemon by individual_id. Returns False if pokemon not found."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if pokemon exists
        cursor.execute("SELECT individual_id FROM captured_pokemon WHERE individual_id = ?", (individual_id,))
        if not cursor.fetchone():
            return False
        
        # Clear old main
        cursor.execute("UPDATE captured_pokemon SET is_main = 0 WHERE is_main = 1")
        # Set new main
        cursor.execute("UPDATE captured_pokemon SET is_main = 1 WHERE individual_id = ?", (individual_id,))
        conn.commit()
        return True

    # --- Item Operations ---

    def save_item(self, item_name: str, quantity: int, extra_data: Optional[Dict] = None):
        """Saves or updates an item."""
        obfuscated_data = self._obfuscate(extra_data) if extra_data else None
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO items (item_name, quantity, data) VALUES (?, ?, ?)",
            (item_name, quantity, obfuscated_data)
        )
        conn.commit()
        return True

    def get_item(self, item_name: str) -> Optional[Dict[str, Any]]:
        """Retrieves an item by name."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT item_name, quantity, data FROM items WHERE item_name = ?",
            (item_name,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "item_name": row["item_name"],
                "quantity": row["quantity"],
                "data": self._deobfuscate(row["data"]) if row["data"] else None
            }
        return None

    def get_all_items(self) -> List[Dict[str, Any]]:
        """Retrieves all items."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, quantity, data FROM items")
        results = []
        for row in cursor.fetchall():
            results.append({
                "item_name": row["item_name"],
                "quantity": row["quantity"],
                "data": self._deobfuscate(row["data"]) if row["data"] else None
            })
        return results

    def update_item_quantity(self, item_name: str, delta: int) -> int:
        """Updates item quantity by delta. Returns new quantity."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get current quantity
        cursor.execute("SELECT quantity FROM items WHERE item_name = ?", (item_name,))
        row = cursor.fetchone()
        current_qty = row["quantity"] if row else 0
        new_qty = max(0, current_qty + delta)

        if new_qty > 0:
            cursor.execute(
                "INSERT OR REPLACE INTO items (item_name, quantity) VALUES (?, ?)",
                (item_name, new_qty)
            )
        else:
            cursor.execute("DELETE FROM items WHERE item_name = ?", (item_name,))

        conn.commit()
        return new_qty

    # --- Badge Operations ---

    def save_badge(self, badge_id: str, badge_data: Dict[str, Any]):
        """Saves or updates a badge."""
        obfuscated_data = self._obfuscate(badge_data)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO badges (badge_id, data) VALUES (?, ?)",
            (badge_id, obfuscated_data)
        )
        conn.commit()
        return True

    def get_badge(self, badge_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a badge by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT data FROM badges WHERE badge_id = ?", (badge_id,))
        row = cursor.fetchone()
        if row:
            return self._deobfuscate(row["data"])
        return None

    def get_all_badges(self) -> List[Dict[str, Any]]:
        """Retrieves all badges."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT badge_id, data FROM badges")
        results = []
        for row in cursor.fetchall():
            badge = self._deobfuscate(row["data"])
            if badge:
                badge["badge_id"] = row["badge_id"]
                results.append(badge)
        return results

    # --- Migration from JSON Files ---

    def migrate_from_json(self, mypokemon_path: Path, mainpokemon_path: Path,
                          items_path: Path, badges_path: Path) -> Dict[str, int]:
        """
        Migrates data from JSON files to the database.
        Returns a dict with counts of migrated items.
        """
        stats = {"pokemon": 0, "main": 0, "items": 0, "badges": 0}

        # Check if already migrated
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = 'migrated'")
        if cursor.fetchone():
            self._log("info", "Database already migrated. Skipping.")
            return stats

        # Migrate mypokemon.json
        if mypokemon_path.is_file():
            try:
                with open(mypokemon_path, 'r', encoding='utf-8') as f:
                    pokemon_list = json.load(f)
                for pokemon in pokemon_list:
                    if self.save_pokemon(pokemon):
                        stats["pokemon"] += 1
                self._log("info", f"Migrated {stats['pokemon']} pokemon from mypokemon.json")
            except Exception as e:
                self._log("error", f"Failed to migrate mypokemon.json: {e}")

        # Migrate mainpokemon.json
        if mainpokemon_path.is_file():
            try:
                with open(mainpokemon_path, 'r', encoding='utf-8') as f:
                    main_data = json.load(f)
                if main_data:
                    # mainpokemon.json is a list with one item
                    main_pokemon = main_data[0] if isinstance(main_data, list) else main_data
                    if self.save_main_pokemon(main_pokemon):
                        stats["main"] = 1
                self._log("info", "Migrated main pokemon from mainpokemon.json")
            except Exception as e:
                self._log("error", f"Failed to migrate mainpokemon.json: {e}")

        # Migrate items.json
        if items_path.is_file():
            try:
                with open(items_path, 'r', encoding='utf-8') as f:
                    items_list = json.load(f)
                for item in items_list:
                    # items.json uses 'item' key, but also support 'name' and 'item_name'
                    item_name = item.get("item") or item.get("name") or item.get("item_name")
                    quantity = item.get("quantity", item.get("amount", 1))
                    if item_name:
                        extra_data = {"type": item.get("type")} if item.get("type") else None
                        self.save_item(item_name, quantity, extra_data)
                        stats["items"] += 1
                self._log("info", f"Migrated {stats['items']} items from items.json")
            except Exception as e:
                self._log("error", f"Failed to migrate items.json: {e}")

        # Migrate badges.json - handles both [1, 2, 3] and [{"id": 1}, ...] formats
        if badges_path.is_file():
            try:
                with open(badges_path, 'r', encoding='utf-8') as f:
                    badges_list = json.load(f)
                for badge in badges_list:
                    # Handle both integer and dict formats
                    if isinstance(badge, int):
                        badge_id = str(badge)
                        badge_data = {"id": badge}
                    else:
                        badge_id = str(badge.get("id", badge.get("badge_id", "")))
                        badge_data = badge
                    if badge_id:
                        self.save_badge(badge_id, badge_data)
                        stats["badges"] += 1
                self._log("info", f"Migrated {stats['badges']} badges from badges.json")
            except Exception as e:
                self._log("error", f"Failed to migrate badges.json: {e}")

        # Mark as migrated
        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('migrated', 'true')"
        )
        conn.commit()

        # --- Integrity Check ---
        # Verify that database counts match expected counts from JSON files
        integrity_issues = []
        
        # Count JSON entries
        json_counts = {"pokemon": 0, "items": 0, "badges": 0}
        try:
            if mypokemon_path.is_file():
                with open(mypokemon_path, 'r', encoding='utf-8') as f:
                    json_counts["pokemon"] = len(json.load(f))
            if items_path.is_file():
                with open(items_path, 'r', encoding='utf-8') as f:
                    json_counts["items"] = len(json.load(f))
            if badges_path.is_file():
                with open(badges_path, 'r', encoding='utf-8') as f:
                    json_counts["badges"] = len(json.load(f))
        except Exception as e:
            self._log("warning", f"Could not read JSON files for integrity check: {e}")
        
        # Count database entries
        db_counts = {"pokemon": 0, "items": 0, "badges": 0}
        cursor.execute("SELECT COUNT(*) FROM all_pokemon")
        db_counts["pokemon"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM items")
        db_counts["items"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM badges")
        db_counts["badges"] = cursor.fetchone()[0]
        
        # Compare counts
        for key in ["pokemon", "items", "badges"]:
            if json_counts[key] > 0 and db_counts[key] < json_counts[key]:
                integrity_issues.append(
                    f"{key}: JSON has {json_counts[key]} entries but DB only has {db_counts[key]}"
                )
        
        if integrity_issues:
            self._log("warning", f"Migration integrity issues detected: {integrity_issues}")
            stats["integrity_issues"] = integrity_issues
        else:
            self._log("info", "Migration integrity check passed - all counts match.")

        self._log("info", f"Migration complete: {stats}")
        return stats

    # --- Utility ---

    def is_migrated(self) -> bool:
        """Checks if JSON data has been migrated to the database."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = 'migrated'")
        row = cursor.fetchone()
        return row is not None and row["value"] == "true"


# Singleton instance for use throughout the addon
_db_instance: Optional[AnkimonDB] = None


def get_db(logger=None) -> AnkimonDB:
    """Gets the singleton database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = AnkimonDB(logger)
    return _db_instance
