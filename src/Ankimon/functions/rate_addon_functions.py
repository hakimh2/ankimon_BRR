import json

from aqt.qt import (
    QDialog,
    QLabel,
    QVBoxLayout,
    )
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    )

import os

from ..resources import rate_path
from ..texts import rate_addon_text_label, thankyou_message_text, dont_show_this_button_text
from ..utils import give_item
from ..singletons import logger, test_window

from aqt import mw

def rate_this_addon():
    # Lazy migration: Check if we have legacy file but no DB entry
    db_rate_this = mw.ankimon_db.get_user_data("rate_this")
    
    if db_rate_this is None:
        # Check for legacy file
        if os.path.exists(rate_path):
            try:
                with open(rate_path, "r", encoding="utf-8") as file:
                    rate_data = json.load(file)
                    if isinstance(rate_data, dict) and rate_data.get("rate_this"):
                        # Migrate to DB
                        mw.ankimon_db.set_user_data("rate_this", "true")
                        db_rate_this = "true"
                
                # Clean up legacy file
                try:
                    os.remove(rate_path)
                except:
                    pass
            except:
                pass

    # Check if already rated (using string comparison as DB stores text)
    if db_rate_this == "true":
        return

    # If we get here, user hasn't rated yet
    rate_window = QDialog()
    rate_window.setWindowTitle("Please Rate this Addon!")

    layout = QVBoxLayout(rate_window)

    text_label = QLabel(rate_addon_text_label)
    layout.addWidget(text_label)

    # Rate button
    rate_button = QPushButton("Rate Now")
    dont_show_button = QPushButton("I dont want to rate this addon.")

    def support_button_click():
        support_url = "https://ko-fi.com/unlucky99"
        QDesktopServices.openUrl(QUrl(support_url))

    def thankyou_message():
        thankyou_window = QDialog()
        thankyou_window.setWindowTitle("Thank you !")
        thx_layout = QVBoxLayout(thankyou_window)
        thx_label = QLabel(thankyou_message_text)
        thx_layout.addWidget(thx_label)
        # Support button
        support_button = QPushButton("Support the Author")
        support_button.clicked.connect(support_button_click)
        thx_layout.addWidget(support_button)
        thankyou_window.setModal(True)
        thankyou_window.exec()

    def dont_show_this_button():
        rate_window.close()
        # Save to DB
        mw.ankimon_db.set_user_data("rate_this", "true")
        logger.log_and_showinfo("info",dont_show_this_button_text)

    def rate_this_button():
        rate_window.close()
        rate_url = "https://ankiweb.net/shared/review/1908235722"
        QDesktopServices.openUrl(QUrl(rate_url))
        thankyou_message()
        
        # Save to DB
        mw.ankimon_db.set_user_data("rate_this", "true")
        
        test_window.rate_display_item("potion")
        # add item to item list
        give_item("potion")
            
    rate_button.clicked.connect(rate_this_button)
    layout.addWidget(rate_button)

    dont_show_button.clicked.connect(dont_show_this_button)
    layout.addWidget(dont_show_button)

    # Support button
    support_button = QPushButton("Support the Author")
    support_button.clicked.connect(support_button_click)
    layout.addWidget(support_button)

    # Make the dialog modal to wait for user interaction
    rate_window.setModal(True)

    # Execute the dialog
    rate_window.exec()