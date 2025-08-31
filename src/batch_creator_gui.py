#!/usr/bin/env python3
"""
360 Batch Account Creator - Desktop GUI
A PySide6-based desktop application for batch account registration.
"""

import sys
import os
import csv
import random
import string
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QPushButton, QTableWidget, QTableWidgetItem, 
    QTextEdit, QProgressBar, QLabel, QFrame, QHeaderView,
    QFileDialog, QMessageBox, QInputDialog, QStatusBar, QSplitter,
    QMenuBar, QMenu
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QThread, QSize, QRect, QCoreApplication
)
from PySide6.QtGui import (
    QFont, QPalette, QColor, QPainter, QPen, QBrush, QIcon, QPixmap, QAction
)

# Import translation manager
from translation_manager import init_translation_manager, get_translation_manager, tr


# Data Models
class AccountStatus(Enum):
    QUEUED = "Queued"
    PROCESSING = "Processing" 
    SUCCESS = "Success"
    FAILED = "Failed"
    
    def get_translated_name(self):
        """Get translated status name"""
        return tr(self.value, "AccountStatus")


@dataclass
class Account:
    id: int
    username: str
    password: str
    status: AccountStatus = AccountStatus.QUEUED
    notes: str = ""


# Custom Status Icon Widget
class StatusIcon(QWidget):
    def __init__(self, status: AccountStatus, parent=None):
        super().__init__(parent)
        self.status = status
        self.setFixedSize(16, 16)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Color mapping
        colors = {
            AccountStatus.QUEUED: QColor("#666666"),
            AccountStatus.PROCESSING: QColor("#0078D4"), 
            AccountStatus.SUCCESS: QColor("#107C10"),
            AccountStatus.FAILED: QColor("#D83B01")
        }
        
        color = colors.get(self.status, QColor("#666666"))
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color))
        
        # Draw icons
        if self.status == AccountStatus.QUEUED:
            # Gray circle
            painter.drawEllipse(4, 4, 8, 8)
        elif self.status == AccountStatus.PROCESSING:
            # Blue spinning indicator (simplified as circle)
            painter.drawEllipse(2, 2, 12, 12)
        elif self.status == AccountStatus.SUCCESS:
            # Green checkmark
            painter.setPen(QPen(color, 3))
            painter.drawLine(3, 8, 7, 12)
            painter.drawLine(7, 12, 13, 6)
        elif self.status == AccountStatus.FAILED:
            # Red X
            painter.setPen(QPen(color, 3))
            painter.drawLine(4, 4, 12, 12)
            painter.drawLine(12, 4, 4, 12)


# Main Application Window
class BatchCreatorMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.accounts: List[Account] = []
        self.current_processing_index = 0
        self.processing_timer = QTimer()
        self.processing_timer.timeout.connect(self.process_next_account)
        self.is_paused = False
        
        # Translation manager
        self.translation_manager = get_translation_manager()
        if self.translation_manager:
            self.translation_manager.languageChanged.connect(self.retranslate_ui)
        
        # Setup logging
        self.setup_logging()
        
        # Initialize UI
        self.init_ui()
        self.apply_styles()
        self.update_button_states()
        
        # Connect signals
        self.connect_signals()
        
        self.log_message(tr("Application started - Ready to import or generate accounts"))
    
    def create_menu_bar(self):
        """Create application menu bar with language selection"""
        menubar = self.menuBar()
        
        # Settings menu
        settings_menu = menubar.addMenu(tr("Settings"))
        
        # Language submenu
        language_menu = settings_menu.addMenu(tr("Language"))
        
        if self.translation_manager:
            languages = self.translation_manager.get_available_languages()
            current_locale = self.translation_manager.get_current_locale()
            
            for locale, info in languages.items():
                action = QAction(info['display_name'], self)
                action.setCheckable(True)
                action.setChecked(locale == current_locale)
                action.triggered.connect(lambda checked, loc=locale: self.change_language(loc))
                language_menu.addAction(action)
    
    def change_language(self, locale: str):
        """Change application language"""
        if self.translation_manager:
            success = self.translation_manager.switch_language(locale)
            if success:
                # Update menu checkmarks
                self.update_language_menu_checks(locale)
    
    def update_language_menu_checks(self, current_locale: str):
        """Update language menu checkmarks"""
        menubar = self.menuBar()
        if menubar.actions():
            settings_menu = menubar.actions()[0].menu()  # First menu is Settings
            if settings_menu and settings_menu.actions():
                language_menu = settings_menu.actions()[0].menu()  # First submenu is Language
                
                if language_menu:
                    languages = self.translation_manager.get_available_languages()
                    for i, (locale, info) in enumerate(languages.items()):
                        if i < len(language_menu.actions()):
                            action = language_menu.actions()[i]
                            action.setChecked(locale == current_locale)
    
    def retranslate_ui(self, locale: str):
        """Retranslate all UI elements when language changes"""
        # Update window title
        self.setWindowTitle(tr("360 Batch Account Creator"))
        
        # Update menu bar
        menubar = self.menuBar()
        menubar.clear()
        self.create_menu_bar()
        
        # Update buttons
        self.btn_import.setText(tr("📁 Import CSV"))
        self.btn_import.setToolTip(tr("Import account data from CSV file"))
        
        self.btn_generate.setText(tr("⚡ Generate Accounts"))
        self.btn_generate.setToolTip(tr("Generate random test accounts"))
        
        self.btn_start.setText(tr("▶️ Start"))
        self.btn_start.setToolTip(tr("Start batch registration process"))
        
        # Update pause button text based on current state
        if self.is_paused:
            self.btn_pause.setText(tr("▶️ Resume"))
        else:
            self.btn_pause.setText(tr("⏸️ Pause"))
        self.btn_pause.setToolTip(tr("Pause/Resume registration process"))
        
        self.btn_stop.setText(tr("⏹️ Stop"))
        self.btn_stop.setToolTip(tr("Stop registration process"))
        
        self.btn_export.setText(tr("💾 Export Results"))
        self.btn_export.setToolTip(tr("Export results to CSV file"))
        
        # Update progress labels
        self.lbl_total_caption.setText(tr("Total:"))
        self.lbl_success_caption.setText(tr("Success:"))
        self.lbl_failed_caption.setText(tr("Failed:"))
        self.lbl_remaining_caption.setText(tr("Remaining:"))
        
        # Update section headers
        self.header_label.setText(tr("Account List"))
        self.log_header_label.setText(tr("Log Output"))
        
        # Update table headers
        self.table_accounts.setHorizontalHeaderLabels([tr("Username"), tr("Status"), tr("Notes")])
        
        # Update table content to refresh status displays
        self.update_table()
        
        # Update status bar if needed
        current_status = self.status_bar.currentMessage()
        if current_status in ["Ready", "准备就绪"]:
            self.status_bar.showMessage(tr("Ready"))
        elif current_status in ["Processing...", "处理中..."]:
            self.status_bar.showMessage(tr("Processing..."))
        elif current_status in ["Paused", "已暂停"]:
            self.status_bar.showMessage(tr("Paused"))
        elif current_status in ["Stopped", "已停止"]:
            self.status_bar.showMessage(tr("Stopped"))
        elif current_status in ["Completed", "已完成"]:
            self.status_bar.showMessage(tr("Completed"))
        
        # Update language button
        self.update_language_button()
    
    def setup_logging(self):
        """Setup logging to both file and GUI"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / 'app.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def init_ui(self):
        """Initialize the main UI components"""
        self.setWindowTitle(tr("360 Batch Account Creator"))
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Control Panel
        self.create_control_panel(main_layout)
        
        # Progress Overview  
        self.create_progress_panel(main_layout)
        
        # Account List Table
        self.create_account_table(main_layout)
        
        # Log Output
        self.create_log_panel(main_layout)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(tr("Ready"))
    
    def create_control_panel(self, parent_layout):
        """Create the top control panel with buttons"""
        panel_frame = QFrame()
        panel_frame.setFrameStyle(QFrame.StyledPanel)
        panel_frame.setMaximumHeight(80)
        parent_layout.addWidget(panel_frame)
        
        layout = QHBoxLayout(panel_frame)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # Import CSV button
        self.btn_import = QPushButton(tr("📁 Import CSV"))
        self.btn_import.setToolTip(tr("Import account data from CSV file"))
        layout.addWidget(self.btn_import)
        
        # Generate Accounts button
        self.btn_generate = QPushButton(tr("⚡ Generate Accounts")) 
        self.btn_generate.setToolTip(tr("Generate random test accounts"))
        layout.addWidget(self.btn_generate)
        
        layout.addItem(self.create_spacer(20))
        
        # Start button (primary)
        self.btn_start = QPushButton(tr("▶️ Start"))
        self.btn_start.setObjectName("primary_button")
        self.btn_start.setToolTip(tr("Start batch registration process"))
        layout.addWidget(self.btn_start)
        
        # Pause button
        self.btn_pause = QPushButton(tr("⏸️ Pause"))
        self.btn_pause.setToolTip(tr("Pause/Resume registration process"))
        layout.addWidget(self.btn_pause)
        
        # Stop button
        self.btn_stop = QPushButton(tr("⏹️ Stop"))
        self.btn_stop.setToolTip(tr("Stop registration process"))
        layout.addWidget(self.btn_stop)
        
        layout.addItem(self.create_spacer(20))
        
        # Export Results button
        self.btn_export = QPushButton(tr("💾 Export Results"))
        self.btn_export.setToolTip(tr("Export results to CSV file"))
        layout.addWidget(self.btn_export)
        
        # Add stretch to push language button to the right
        layout.addStretch()
        
        # Language switch button (right-aligned)
        self.btn_language = QPushButton()
        self.btn_language.setToolTip(tr("Switch language / 切换语言"))
        self.btn_language.setMaximumWidth(50)  # Wider for full icon display
        self.btn_language.setMinimumWidth(50)   # Fixed width
        self.update_language_button()
        layout.addWidget(self.btn_language)
    
    def create_progress_panel(self, parent_layout):
        """Create progress overview panel"""
        panel_frame = QFrame()
        panel_frame.setFrameStyle(QFrame.StyledPanel) 
        panel_frame.setMaximumHeight(60)
        parent_layout.addWidget(panel_frame)
        
        layout = QHBoxLayout(panel_frame)
        layout.setContentsMargins(16, 8, 16, 8)
        
        # Progress bar
        progress_layout = QVBoxLayout()
        progress_label = QLabel(tr("Progress:"))
        progress_label.setFont(QFont("", 9))
        progress_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(20)
        progress_layout.addWidget(self.progress_bar)
        layout.addLayout(progress_layout, 2)
        
        layout.addItem(self.create_spacer(32))
        
        # Statistics
        stats_layout = QGridLayout()
        
        # Total
        self.lbl_total_caption = QLabel(tr("Total:"))
        stats_layout.addWidget(self.lbl_total_caption, 0, 0)
        self.lbl_total = QLabel("0")
        self.lbl_total.setStyleSheet("font-weight: bold;")
        stats_layout.addWidget(self.lbl_total, 0, 1)
        
        # Success  
        self.lbl_success_caption = QLabel(tr("Success:"))
        stats_layout.addWidget(self.lbl_success_caption, 0, 2)
        self.lbl_success = QLabel("0")
        self.lbl_success.setStyleSheet("font-weight: bold; color: #107C10;")
        stats_layout.addWidget(self.lbl_success, 0, 3)
        
        # Failed
        self.lbl_failed_caption = QLabel(tr("Failed:"))
        stats_layout.addWidget(self.lbl_failed_caption, 1, 0)
        self.lbl_failed = QLabel("0")
        self.lbl_failed.setStyleSheet("font-weight: bold; color: #D83B01;")
        stats_layout.addWidget(self.lbl_failed, 1, 1)
        
        # Remaining
        self.lbl_remaining_caption = QLabel(tr("Remaining:"))
        stats_layout.addWidget(self.lbl_remaining_caption, 1, 2)
        self.lbl_remaining = QLabel("0")
        self.lbl_remaining.setStyleSheet("font-weight: bold; color: #666666;")
        stats_layout.addWidget(self.lbl_remaining, 1, 3)
        
        layout.addLayout(stats_layout, 1)
    
    def create_account_table(self, parent_layout):
        """Create the main account list table"""
        # Table container
        table_frame = QFrame()
        table_frame.setFrameStyle(QFrame.StyledPanel)
        parent_layout.addWidget(table_frame, 1)  # Expandable
        
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(8, 8, 8, 8)
        
        # Table header
        self.header_label = QLabel(tr("Account List"))
        self.header_label.setFont(QFont("", 10, QFont.Bold))
        table_layout.addWidget(self.header_label)
        
        # Table widget
        self.table_accounts = QTableWidget()
        self.table_accounts.setColumnCount(3)
        self.table_accounts.setHorizontalHeaderLabels([tr("Username"), tr("Status"), tr("Notes")])
        
        # Configure table
        header = self.table_accounts.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Username
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)        # Status  
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)      # Notes
        header.resizeSection(1, 120)  # Fixed width for status column
        
        self.table_accounts.setAlternatingRowColors(True)
        self.table_accounts.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_accounts.verticalHeader().setVisible(False)
        
        table_layout.addWidget(self.table_accounts)
    
    def create_log_panel(self, parent_layout):
        """Create bottom log output panel"""
        panel_frame = QFrame()
        panel_frame.setFrameStyle(QFrame.StyledPanel)
        panel_frame.setMaximumHeight(150)
        parent_layout.addWidget(panel_frame)
        
        layout = QVBoxLayout(panel_frame)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Log header
        self.log_header_label = QLabel(tr("Log Output"))
        self.log_header_label.setFont(QFont("", 10, QFont.Bold))
        layout.addWidget(self.log_header_label)
        
        # Log text area
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(120)
        self.txt_log.setFont(QFont("Consolas, Monaco, monospace", 9))
        layout.addWidget(self.txt_log)
    
    def create_spacer(self, width):
        """Create horizontal spacer"""
        from PySide6.QtWidgets import QSpacerItem, QSizePolicy
        return QSpacerItem(width, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
    
    def apply_styles(self):
        """Apply custom styles to the application"""
        style = """
        QMainWindow {
            background-color: #F5F5F5;
        }
        
        QFrame {
            background-color: white;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
        }
        
        QPushButton {
            background-color: white;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 11px;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background-color: #F0F0F0;
            border-color: #0078D4;
        }
        
        QPushButton:pressed {
            background-color: #E0E0E0;
        }
        
        QPushButton:disabled {
            background-color: #F5F5F5;
            color: #999999;
            border-color: #E0E0E0;
        }
        
        QPushButton#primary_button {
            background-color: #0078D4;
            color: white;
            border-color: #0078D4;
            font-weight: bold;
        }
        
        QPushButton#primary_button:hover {
            background-color: #106EBE;
        }
        
        QPushButton#primary_button:disabled {
            background-color: #CCCCCC;
            color: #999999;
        }
        
        QTableWidget {
            background-color: white;
            border: 1px solid #E0E0E0;
            gridline-color: #F0F0F0;
        }
        
        QTableWidget::item {
            padding: 4px 8px;
            border: none;
        }
        
        QTableWidget::item:selected {
            background-color: #E3F2FD;
        }
        
        QHeaderView::section {
            background-color: #F8F9FA;
            border: 1px solid #E0E0E0;
            padding: 4px 8px;
            font-weight: bold;
        }
        
        QProgressBar {
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            text-align: center;
        }
        
        QProgressBar::chunk {
            background-color: #0078D4;
            border-radius: 3px;
        }
        
        QTextEdit {
            background-color: #FAFAFA;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
        }
        """
        self.setStyleSheet(style)
    
    def connect_signals(self):
        """Connect button signals to their handlers"""
        self.btn_import.clicked.connect(self.import_csv)
        self.btn_generate.clicked.connect(self.generate_accounts)
        self.btn_start.clicked.connect(self.start_processing)
        self.btn_pause.clicked.connect(self.pause_processing)
        self.btn_stop.clicked.connect(self.stop_processing)
        self.btn_export.clicked.connect(self.export_results)
        self.btn_language.clicked.connect(self.toggle_language)
    
    def update_button_states(self):
        """Update button enabled/disabled states based on current state"""
        has_accounts = len(self.accounts) > 0
        is_processing = self.processing_timer.isActive()
        
        self.btn_import.setEnabled(not is_processing)
        self.btn_generate.setEnabled(not is_processing)
        self.btn_start.setEnabled(has_accounts and not is_processing)
        self.btn_pause.setEnabled(is_processing)
        self.btn_stop.setEnabled(is_processing)
        self.btn_export.setEnabled(has_accounts)
        
        # Update pause button text
        if self.is_paused:
            self.btn_pause.setText(tr("▶️ Resume"))
        else:
            self.btn_pause.setText(tr("⏸️ Pause"))
    
    def update_statistics(self):
        """Update the statistics display"""
        total = len(self.accounts)
        success = len([acc for acc in self.accounts if acc.status == AccountStatus.SUCCESS])
        failed = len([acc for acc in self.accounts if acc.status == AccountStatus.FAILED])
        remaining = total - success - failed
        
        self.lbl_total.setText(str(total))
        self.lbl_success.setText(str(success))
        self.lbl_failed.setText(str(failed))
        self.lbl_remaining.setText(str(remaining))
        
        # Update progress bar
        if total > 0:
            progress = int((success + failed) * 100 / total)
            self.progress_bar.setValue(progress)
        else:
            self.progress_bar.setValue(0)
    
    def update_table(self):
        """Update the account table display"""
        self.table_accounts.setRowCount(len(self.accounts))
        
        for row, account in enumerate(self.accounts):
            # Username
            self.table_accounts.setItem(row, 0, QTableWidgetItem(account.username))
            
            # Status with icon and text
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(8, 4, 8, 4)
            status_layout.setSpacing(8)
            
            # Status icon
            icon = StatusIcon(account.status)
            status_layout.addWidget(icon)
            
            # Status text
            status_text = QLabel(account.status.get_translated_name())
            status_colors = {
                AccountStatus.QUEUED: "#666666",
                AccountStatus.PROCESSING: "#0078D4",
                AccountStatus.SUCCESS: "#107C10", 
                AccountStatus.FAILED: "#D83B01"
            }
            color = status_colors.get(account.status, "#000000")
            status_text.setStyleSheet(f"color: {color}; font-weight: bold;")
            status_layout.addWidget(status_text)
            status_layout.addStretch()
            
            self.table_accounts.setCellWidget(row, 1, status_widget)
            
            # Notes
            self.table_accounts.setItem(row, 2, QTableWidgetItem(account.notes))
    
    def log_message(self, message: str):
        """Add a message to the log output"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.txt_log.append(formatted_message)
        self.logger.info(message)
        
        # Auto-scroll to bottom
        cursor = self.txt_log.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.txt_log.setTextCursor(cursor)
    
    # Button Event Handlers
    def import_csv(self):
        """Import accounts from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("Import CSV File"), "", tr("CSV Files (*.csv)")
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                accounts = []
                
                for i, row in enumerate(reader):
                    username = row.get('username', '').strip()
                    password = row.get('password', '').strip()
                    
                    if username and password:
                        account = Account(
                            id=i + 1,
                            username=username,
                            password=password
                        )
                        accounts.append(account)
                
                self.accounts = accounts
                self.update_table()
                self.update_statistics()
                self.update_button_states()
                
                self.log_message(tr("Successfully imported %1 accounts from CSV").arg(len(accounts)))
                QMessageBox.information(self, tr("Success"), 
                    tr("Imported %1 accounts successfully!").arg(len(accounts)))
                
        except Exception as e:
            self.log_message(tr("Failed to import CSV: %1").arg(str(e)))
            QMessageBox.critical(self, tr("Error"), tr("Failed to import CSV file:\n%1").arg(str(e)))
    
    def generate_accounts(self):
        """Generate random test accounts"""
        count, ok = QInputDialog.getInt(
            self, tr("Generate Accounts"), 
            tr("How many accounts to generate?"),
            value=10, min=1, max=1000
        )
        
        if not ok:
            return
        
        accounts = []
        for i in range(count):
            username = f"user_{''.join(random.choices(string.ascii_lowercase, k=6))}_{i+1:03d}"
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            
            account = Account(
                id=i + 1,
                username=username,
                password=password
            )
            accounts.append(account)
        
        self.accounts = accounts
        self.update_table()
        self.update_statistics()
        self.update_button_states()
        
        self.log_message(tr("Generated %1 random accounts").arg(count))
        QMessageBox.information(self, tr("Success"), 
            tr("Generated %1 accounts successfully!").arg(count))
    
    def start_processing(self):
        """Start the batch processing"""
        if not self.accounts:
            return
        
        self.current_processing_index = 0
        self.is_paused = False
        
        # Reset all accounts to queued status
        for account in self.accounts:
            account.status = AccountStatus.QUEUED
            account.notes = ""
        
        self.update_table()
        self.update_statistics()
        self.update_button_states()
        
        # Start processing timer (simulate registration process)
        self.processing_timer.start(1500)  # 1.5 seconds per account
        
        self.log_message(tr("Started batch processing for %1 accounts").arg(len(self.accounts)))
        self.status_bar.showMessage(tr("Processing..."))
    
    def pause_processing(self):
        """Pause or resume processing"""
        if self.processing_timer.isActive():
            if self.is_paused:
                # Resume
                self.processing_timer.start()
                self.is_paused = False
                self.log_message(tr("Processing resumed"))
                self.status_bar.showMessage(tr("Processing..."))
            else:
                # Pause
                self.processing_timer.stop()
                self.is_paused = True
                self.log_message(tr("Processing paused"))
                self.status_bar.showMessage(tr("Paused"))
        
        self.update_button_states()
    
    def stop_processing(self):
        """Stop processing completely"""
        self.processing_timer.stop()
        self.is_paused = False
        self.current_processing_index = 0
        
        # Reset any processing accounts to queued
        for account in self.accounts:
            if account.status == AccountStatus.PROCESSING:
                account.status = AccountStatus.QUEUED
                account.notes = ""
        
        self.update_table()
        self.update_statistics()
        self.update_button_states()
        
        self.log_message(tr("Processing stopped"))
        self.status_bar.showMessage(tr("Stopped"))
    
    def process_next_account(self):
        """Process the next account (simulation)"""
        if self.current_processing_index >= len(self.accounts):
            # All accounts processed
            self.processing_timer.stop()
            self.is_paused = False
            self.update_button_states()
            self.log_message(tr("Batch processing completed!"))
            self.status_bar.showMessage(tr("Completed"))
            
            # Show completion message
            success_count = len([acc for acc in self.accounts if acc.status == AccountStatus.SUCCESS])
            failed_count = len([acc for acc in self.accounts if acc.status == AccountStatus.FAILED])
            
            QMessageBox.information(self, tr("Processing Complete"), 
                tr("Batch processing completed!\n\nSuccess: %1\nFailed: %2").arg(success_count).arg(failed_count))
            return
        
        # Get current account
        account = self.accounts[self.current_processing_index]
        account.status = AccountStatus.PROCESSING
        account.notes = tr("Registering account...", "FailureReasons")
        
        self.update_table()
        self.update_statistics()
        
        self.log_message(tr("Processing account: %1").arg(account.username))
        
        # Simulate processing result (80% success rate)
        QTimer.singleShot(800, self.complete_current_account)
    
    def complete_current_account(self):
        """Complete processing of current account"""
        if self.current_processing_index >= len(self.accounts):
            return
        
        account = self.accounts[self.current_processing_index]
        
        # Simulate random success/failure (80% success rate)
        if random.random() < 0.8:
            account.status = AccountStatus.SUCCESS
            account.notes = tr("Registered successfully", "FailureReasons")
            self.log_message(tr("SUCCESS: %1 registered successfully").arg(account.username))
        else:
            account.status = AccountStatus.FAILED
            failure_reasons = [
                tr("Username already taken", "FailureReasons"),
                tr("Invalid email format", "FailureReasons"), 
                tr("Network timeout", "FailureReasons"),
                tr("Captcha required", "FailureReasons"),
                tr("Rate limit exceeded", "FailureReasons")
            ]
            account.notes = random.choice(failure_reasons)
            self.log_message(tr("FAILED: %1 - %2").arg(account.username).arg(account.notes))
        
        self.current_processing_index += 1
        
        self.update_table()
        self.update_statistics()
    
    def export_results(self):
        """Export results to CSV file"""
        if not self.accounts:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("Export Results"), 
            f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            tr("CSV Files (*.csv)")
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['Username', 'Password', 'Status', 'Notes', 'Timestamp'])
                
                for account in self.accounts:
                    writer.writerow([
                        account.username,
                        account.password,
                        account.status.value,
                        account.notes,
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ])
            
            self.log_message(tr("Results exported to: %1").arg(file_path))
            QMessageBox.information(self, tr("Success"), 
                tr("Results exported successfully!\n\nFile: %1").arg(os.path.basename(file_path)))
            
        except Exception as e:
            self.log_message(tr("Failed to export results: %1").arg(str(e)))
            QMessageBox.critical(self, tr("Error"), tr("Failed to export results:\n%1").arg(str(e)))
    
    # Language related methods
    def update_language_button(self):
        """Update language button text based on current language"""
        # Only show icon, no text
        self.btn_language.setText("🌐")
    
    def toggle_language(self):
        """Toggle between Chinese and English"""
        translation_manager = get_translation_manager()
        current_locale = translation_manager.get_current_locale()
        
        # Switch to the other language
        if current_locale == 'zh-CN':
            new_locale = 'en-US'
            self.log_message(tr("Switching to English..."))
        else:
            new_locale = 'zh-CN'
            self.log_message(tr("切换至中文..."))
        
        # Apply the new language
        success = translation_manager.switch_language(new_locale)
        if success:
            self.retranslate_ui(new_locale)
            self.log_message(tr("Language switched successfully!"))
        else:
            self.log_message(f"Failed to switch language to {new_locale}")
            QMessageBox.warning(self, "Error", f"Failed to switch language to {new_locale}")


# Main Application Class
class BatchCreatorApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        
        # Application settings
        self.setApplicationName("360 Batch Account Creator")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("360 Tools")
        
        # Initialize translation manager
        self.translation_manager = init_translation_manager(self)
        self.translation_manager.initialize_language()
        
        # Create main window
        self.main_window = BatchCreatorMainWindow()
    
    def run(self):
        """Run the application"""
        self.main_window.show()
        return self.exec()


def main():
    """Main entry point"""
    app = BatchCreatorApp(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()