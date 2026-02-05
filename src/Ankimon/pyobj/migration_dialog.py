"""
Migration Dialog for Ankimon Database

Shows a blocking dialog when migrating from JSON to SQLite storage.
The program is not usable until migration completes.
"""

import json
import shutil
import traceback
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QApplication, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from pathlib import Path
from typing import Dict, Any

from ..utils import show_warning_with_traceback


class MigrationDialog(QDialog):
    """Blocking dialog for database migration."""
    
    def __init__(self, db, mypokemon_path, mainpokemon_path, items_path, badges_path, parent=None):
        super().__init__(parent)
        self.db = db
        self.mypokemon_path = Path(mypokemon_path)
        self.mainpokemon_path = Path(mainpokemon_path)
        self.items_path = Path(items_path)
        self.badges_path = Path(badges_path)
        self.migration_successful = False
        self.migration_running = False
        self.cancelled = False
        
        self.setWindowTitle("Ankimon Data Migration")
        self.setMinimumSize(500, 380)
        self.setModal(True)  # Block interaction with parent
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("📦 Database Migration Required")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel(
            "Ankimon is upgrading to a new, faster storage system!\n\n"
            "Your Pokemon collection will be migrated to a secure database.\n"
            "This is a one-time process."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Click 'Start Migration' to begin.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Progress log
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(120)
        layout.addWidget(self.log_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🚀 Start Migration")
        self.start_button.setMinimumHeight(40)
        self.start_button.clicked.connect(self._run_migration)
        button_layout.addWidget(self.start_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_button)
        
        self.continue_button = QPushButton("Continue")
        self.continue_button.setMinimumHeight(40)
        self.continue_button.hide()
        self.continue_button.clicked.connect(self.accept)
        button_layout.addWidget(self.continue_button)
        
        layout.addLayout(button_layout)
    
    def _update_progress(self, percent: int, message: str):
        """Update progress bar and log."""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
        self.log_area.append(message)
        QApplication.processEvents()  # Force UI update
    
    def _on_cancel(self):
        """Handle cancel button click."""
        if self.migration_running:
            reply = QMessageBox.question(
                self, "Cancel Migration",
                "Migration is in progress. Are you sure you want to cancel?\n\n"
                "Note: Partial data may remain in the database.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.cancelled = True
                self._update_progress(0, "⚠ Migration cancelled by user.")
        else:
            # Not started yet, just close
            self.reject()
    
    def _run_migration(self):
        """Run migration in foreground (blocking)."""
        self.migration_running = True
        self.start_button.setEnabled(False)
        self.start_button.setText("Migrating...")
        stats = {"pokemon": 0, "main": 0, "items": 0, "badges": 0}
        
        try:
            # Step 1: Migrate mypokemon.json (70% of progress)
            if self.mypokemon_path.is_file() and not self.cancelled:
                self._update_progress(5, "Loading Pokemon collection...")
                with open(self.mypokemon_path, 'r', encoding='utf-8') as f:
                    pokemon_list = json.load(f)
                
                total = len(pokemon_list)
                for i, pokemon in enumerate(pokemon_list):
                    if self.cancelled:
                        break
                    if self.db.save_pokemon(pokemon):
                        stats["pokemon"] += 1
                    # Update progress every 20 pokemon or at milestones
                    if total > 0 and (i % 20 == 0 or i == total - 1):
                        pct = 5 + int((i / total) * 65)
                        self._update_progress(pct, f"Migrating Pokemon {i + 1}/{total}...")
                
                if not self.cancelled:
                    self._update_progress(70, f"✓ Migrated {stats['pokemon']} Pokemon")
            elif not self.mypokemon_path.is_file():
                self._update_progress(70, "No Pokemon collection found.")
            
            if self.cancelled:
                self._finish_cancelled()
                return
            
            # Step 2: Migrate mainpokemon.json (10% of progress)
            if self.mainpokemon_path.is_file():
                self._update_progress(75, "Migrating main Pokemon...")
                with open(self.mainpokemon_path, 'r', encoding='utf-8') as f:
                    main_data = json.load(f)
                if main_data:
                    main_pokemon = main_data[0] if isinstance(main_data, list) else main_data
                    if self.db.save_main_pokemon(main_pokemon):
                        stats["main"] = 1
                self._update_progress(80, "✓ Migrated main Pokemon")
            
            if self.cancelled:
                self._finish_cancelled()
                return
            
            # Step 3: Migrate items.json (10% of progress)
            if self.items_path.is_file():
                self._update_progress(82, "Migrating items...")
                with open(self.items_path, 'r', encoding='utf-8') as f:
                    items_list = json.load(f)
                for item in items_list:
                    if self.cancelled:
                        break
                    item_name = item.get("name") or item.get("item_name")
                    quantity = item.get("quantity", item.get("amount", 1))
                    if item_name:
                        self.db.save_item(item_name, quantity, item)
                        stats["items"] += 1
                if not self.cancelled:
                    self._update_progress(90, f"✓ Migrated {stats['items']} items")
            
            if self.cancelled:
                self._finish_cancelled()
                return
            
            # Step 4: Migrate badges.json (10% of progress)
            if self.badges_path.is_file():
                self._update_progress(92, "Migrating badges...")
                with open(self.badges_path, 'r', encoding='utf-8') as f:
                    badges_list = json.load(f)
                for badge in badges_list:
                    if self.cancelled:
                        break
                    # Handle both integer and dict formats
                    if isinstance(badge, int):
                        badge_id = str(badge)
                        badge_data = {"id": badge}
                    else:
                        badge_id = str(badge.get("id", badge.get("badge_id", "")))
                        badge_data = badge
                    if badge_id:
                        self.db.save_badge(badge_id, badge_data)
                        stats["badges"] += 1
                if not self.cancelled:
                    self._update_progress(98, f"✓ Migrated {stats['badges']} badges")
            
            if self.cancelled:
                self._finish_cancelled()
                return
            
            # Mark as migrated
            conn = self.db._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES ('migrated', 'true')"
            )
            conn.commit()
            
            # Delete JSON files only after successful migration
            self._update_progress(99, "Cleaning up old JSON files...")
            self._cleanup_json_files()
            
            self._update_progress(100, "🎉 Migration complete!")
            self.log_area.append(
                f"\n📊 Summary: {stats['pokemon']} Pokemon, "
                f"{stats['items']} items, {stats['badges']} badges"
            )
            self.migration_successful = True
            self.migration_running = False
            self.start_button.hide()
            self.cancel_button.hide()
            self.continue_button.show()
            
        except Exception as e:
            self.migration_running = False
            error_msg = f"❌ Error: {e}"
            self._update_progress(0, error_msg)
            self.log_area.append("\nMigration failed. Your original files are preserved.")
            self.log_area.append(f"\n--- Full Error Traceback ---\n{traceback.format_exc()}")
            self.start_button.setEnabled(True)
            self.start_button.setText("🔄 Retry")
            # Show detailed error dialog
            try:
                show_warning_with_traceback(
                    exception=e,
                    message="Migration failed! Please report this error:"
                )
            except:
                # Fallback if show_warning_with_traceback isn't available
                QMessageBox.critical(
                    self, "Migration Error",
                    f"Migration failed:\n\n{e}\n\nPlease report this error."
                )
    
    def _finish_cancelled(self):
        """Handle cancelled migration."""
        self.migration_running = False
        self.log_area.append("\n⚠ Migration was cancelled. Original files preserved.")
        self.start_button.setEnabled(True)
        self.start_button.setText("🔄 Retry")
    
    def _cleanup_json_files(self):
        \"\"\"Move old JSON files to json/ subfolder after successful migration.\"\"\"
        # Move to user_files/json/ - ensures path change breaks any remaining JSON usage
        backup_dir = self.mypokemon_path.parent / \"json\"
        backup_dir.mkdir(exist_ok=True)
        
        files_to_backup = [
            self.mypokemon_path,
            self.mainpokemon_path,
            self.items_path,
            self.badges_path
        ]
        
        for file_path in files_to_backup:
            if file_path.is_file():
                try:
                    # Move to backup instead of delete
                    dest = backup_dir / file_path.name
                    shutil.move(str(file_path), str(dest))
                    self.log_area.append(f"  Backed up: {file_path.name}")
                except Exception as e:
                    self.log_area.append(f"  ⚠ Could not backup {file_path.name}: {e}")
        
        self.log_area.append(f"  Old files moved to: {backup_dir.name}/")
    
    def closeEvent(self, event):
        """Prevent closing until migration is complete or cancelled."""
        if self.migration_running:
            event.ignore()
            QMessageBox.warning(self, "Please Wait", "Migration is in progress.")
        else:
            event.accept()


def show_migration_dialog_if_needed(db, mypokemon_path, mainpokemon_path, 
                                     items_path, badges_path, parent=None) -> bool:
    """
    Shows the migration dialog if migration is needed.
    Blocks until migration is complete.
    
    Returns:
        True if migration was successful or already done, False otherwise.
    """
    if db.is_migrated():
        return True
    
    dialog = MigrationDialog(
        db, mypokemon_path, mainpokemon_path, items_path, badges_path, parent
    )
    dialog.exec()
    
    return dialog.migration_successful
