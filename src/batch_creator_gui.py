#!/usr/bin/env python3
"""
360 Batch Account Creator - Main Application with MVVM Architecture
A PySide6-based desktop application for batch account registration.
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QPushButton, QTableWidget, QTableWidgetItem, 
    QTextEdit, QProgressBar, QLabel, QFrame, QHeaderView,
    QFileDialog, QMessageBox, QInputDialog, QStatusBar,
    QMenuBar, QMenu, QSystemTrayIcon
)
from PySide6.QtCore import Qt, QSize, QRect, QCoreApplication
from PySide6.QtGui import (
    QFont, QPalette, QColor, QPainter, QPen, QBrush, QIcon, QPixmap, 
    QAction, QClipboard
)

# Import translation manager
from .translation_manager import tr

# Import business logic
from .models.account import Account, AccountStatus
from .viewmodels.batch_creator_viewmodel import BatchCreatorViewModel


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
            AccountStatus.CAPTCHA_PENDING: QColor("#FFA500"),  # Orange for waiting captcha
            AccountStatus.SUCCESS: QColor("#107C10"),
            AccountStatus.FAILED: QColor("#D83B01")
        }
        
        color = colors.get(self.status, QColor("#666666"))
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color))
        
        # Draw icons
        if self.status == AccountStatus.QUEUED:
            painter.drawEllipse(4, 4, 8, 8)
        elif self.status == AccountStatus.PROCESSING:
            painter.drawEllipse(2, 2, 12, 12)
        elif self.status == AccountStatus.CAPTCHA_PENDING:
            # Draw exclamation mark for captcha waiting
            painter.setPen(QPen(color, 2))
            painter.drawLine(8, 3, 8, 10)  # Vertical line
            painter.drawRect(7, 12, 2, 2)  # Dot
        elif self.status == AccountStatus.SUCCESS:
            painter.setPen(QPen(color, 3))
            painter.drawLine(3, 8, 7, 12)
            painter.drawLine(7, 12, 13, 6)
        elif self.status == AccountStatus.FAILED:
            painter.setPen(QPen(color, 3))
            painter.drawLine(4, 4, 12, 12)
            painter.drawLine(12, 4, 4, 12)


# Custom Table Cell Components
class CopyableTextWidget(QWidget):
    """Widget with text and copy button"""
    def __init__(self, text: str, viewmodel: BatchCreatorViewModel, parent=None):
        super().__init__(parent)
        self.text = text
        self.viewmodel = viewmodel
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        self.label = QLabel(text)
        layout.addWidget(self.label)
        
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setFixedSize(50, 24)
        self.copy_btn.setStyleSheet("font-size: 10px;")
        self.copy_btn.setToolTip(tr("Copy to clipboard"))
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(self.copy_btn)
        
        layout.addStretch()
    
    def copy_to_clipboard(self):
        self.viewmodel.copy_text_to_clipboard(self.text)
    
    def update_text(self, text: str):
        self.text = text
        self.label.setText(text)


class PasswordWidget(QWidget):
    """Widget with password field, visibility toggle and copy button"""
    def __init__(self, password: str, viewmodel: BatchCreatorViewModel, parent=None):
        super().__init__(parent)
        self.password = password
        self.is_visible = False
        self.viewmodel = viewmodel
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        self.label = QLabel(self.get_display_text())
        layout.addWidget(self.label)
        
        self.eye_btn = QPushButton("Show")
        self.eye_btn.setFixedSize(50, 24)
        self.eye_btn.setStyleSheet("font-size: 10px;")
        self.eye_btn.setToolTip(tr("Toggle password visibility"))
        self.eye_btn.clicked.connect(self.toggle_visibility)
        layout.addWidget(self.eye_btn)
        
        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setFixedSize(50, 24)
        self.copy_btn.setStyleSheet("font-size: 10px;")
        self.copy_btn.setToolTip(tr("Copy password to clipboard"))
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(self.copy_btn)
        
        layout.addStretch()
    
    def get_display_text(self):
        return self.password if self.is_visible else "*" * len(self.password)
    
    def toggle_visibility(self):
        self.is_visible = not self.is_visible
        self.label.setText(self.get_display_text())
        # Toggle between Show/Hide text
        self.eye_btn.setText("Hide" if self.is_visible else "Show")
    
    def copy_to_clipboard(self):
        self.viewmodel.copy_text_to_clipboard(self.password)
    
    def update_password(self, password: str):
        self.password = password
        self.label.setText(self.get_display_text())


# Main Application Window
class BatchCreatorMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Initialize ViewModel
        self.viewmodel = BatchCreatorViewModel()
        
        # Setup logging
        self.setup_logging()
        
        # Initialize UI
        self.init_ui()
        self.apply_styles()
        
        # Connect ViewModel signals
        self.connect_viewmodel_signals()
        
        # Initial UI update
        self.update_button_states()
        self.update_statistics()
        self.update_table()
    
    def setup_logging(self):
        """Setup logging to both file and GUI"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
    
    def init_ui(self):
        """Initialize the main UI components"""
        self.setWindowTitle(tr("360 Batch Account Creator"))
        self.setMinimumSize(1000, 700)  # Wider for password column
        self.resize(1200, 800)
        
        # Central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Create menu bar
        self.create_menu_bar()
        
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
    
    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()
        
        # Settings menu
        settings_menu = menubar.addMenu(tr("Settings"))
        
        # Language submenu
        language_menu = settings_menu.addMenu(tr("Language"))
        
        # Chinese action
        chinese_action = QAction(tr("Chinese"), self)
        chinese_action.triggered.connect(lambda: self.switch_language('zh-CN'))
        language_menu.addAction(chinese_action)
        
        # English action
        english_action = QAction(tr("English"), self)
        english_action.triggered.connect(lambda: self.switch_language('en-US'))
        language_menu.addAction(english_action)
    
    def switch_language(self, locale: str):
        """Switch application language"""
        translation_manager = get_translation_manager()
        success = translation_manager.switch_language(locale)
        if success:
            self.retranslate_ui(locale)
    
    def retranslate_ui(self, locale: str):
        """Retranslate all UI elements when language changes"""
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
        
        if self.viewmodel.is_paused:
            self.btn_pause.setText(tr("▶️ Resume"))
        else:
            self.btn_pause.setText(tr("⏸️ Pause"))
        self.btn_pause.setToolTip(tr("Pause/Resume registration process"))
        
        self.btn_stop.setText(tr("⏹️ Stop"))
        self.btn_stop.setToolTip(tr("Stop registration process"))
        
        self.btn_export.setText(tr("💾 Export Results"))
        self.btn_export.setToolTip(tr("Export results to CSV file"))
        
        self.btn_manual_captcha.setText(tr("🔍 Manual Captcha Check"))
        self.btn_manual_captcha.setToolTip(tr("Manually check if captcha has been completed"))
        
        # Update progress labels
        self.lbl_total_caption.setText(tr("Total:"))
        self.lbl_success_caption.setText(tr("Success:"))
        self.lbl_failed_caption.setText(tr("Failed:"))
        self.lbl_remaining_caption.setText(tr("Remaining:"))
        
        # Update section headers
        self.header_label.setText(tr("Account List"))
        self.log_header_label.setText(tr("Log Output"))
        
        # Update table headers
        self.table_accounts.setHorizontalHeaderLabels([
            tr("Username"), tr("Password"), tr("Status"), tr("Notes")
        ])
        
        # Update table content
        self.update_table()
        
        # Update language button
        self.update_language_button()
    
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
        
        # Manual Captcha Detection button (Phase 2 feature)
        self.btn_manual_captcha = QPushButton(tr("🔍 Manual Captcha Check"))
        self.btn_manual_captcha.setToolTip(tr("Manually check if captcha has been completed"))
        self.btn_manual_captcha.setEnabled(False)  # Initially disabled
        layout.addWidget(self.btn_manual_captcha)
        
        # Add stretch to push language button to the right
        layout.addStretch()
        
        # Language switch button (right-aligned)
        self.btn_language = QPushButton()
        self.btn_language.setToolTip(tr("Switch language / 切换语言"))
        self.btn_language.setMaximumWidth(50)
        self.btn_language.setMinimumWidth(50)
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
        table_frame = QFrame()
        table_frame.setFrameStyle(QFrame.StyledPanel)
        parent_layout.addWidget(table_frame, 1)
        
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(8, 8, 8, 8)
        
        self.header_label = QLabel(tr("Account List"))
        self.header_label.setFont(QFont("", 10, QFont.Bold))
        table_layout.addWidget(self.header_label)
        
        self.table_accounts = QTableWidget()
        self.table_accounts.setColumnCount(4)
        self.table_accounts.setHorizontalHeaderLabels([
            tr("Username"), tr("Password"), tr("Status"), tr("Notes")
        ])
        
        # Configure table
        header = self.table_accounts.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Username
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Password  
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)        # Status  
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)      # Notes
        header.resizeSection(1, 200)  # Password column
        header.resizeSection(2, 140)  # Status column
        
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
        
        self.log_header_label = QLabel(tr("Log Output"))
        self.log_header_label.setFont(QFont("", 10, QFont.Bold))
        layout.addWidget(self.log_header_label)
        
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
    
    def connect_viewmodel_signals(self):
        """Connect ViewModel signals to UI update methods"""
        self.viewmodel.accounts_changed.connect(self.update_table)
        self.viewmodel.accounts_changed.connect(self.update_button_states)  # Fix: Update button states when accounts change
        self.viewmodel.statistics_changed.connect(self.update_statistics)
        self.viewmodel.processing_status_changed.connect(self.update_button_states)
        self.viewmodel.log_message.connect(self.log_message)
        self.viewmodel.batch_processing_completed.connect(self.on_batch_complete)
        self.viewmodel.language_changed.connect(self.on_language_changed)  # New language signal
        
        # Connect captcha-related signals (MVVM View layer integration)
        self.viewmodel.captcha_detected.connect(self.on_captcha_detected)
        self.viewmodel.captcha_resolved.connect(self.on_captcha_resolved)
        self.viewmodel.captcha_timeout.connect(self.on_captcha_timeout)
        
        # Connect button signals
        self.btn_import.clicked.connect(self.import_csv)
        self.btn_generate.clicked.connect(self.generate_accounts)
        self.btn_start.clicked.connect(self.start_processing)
        self.btn_pause.clicked.connect(self.pause_processing)
        self.btn_stop.clicked.connect(self.stop_processing)
        self.btn_export.clicked.connect(self.export_results)
        self.btn_manual_captcha.clicked.connect(self.manual_captcha_check)
        self.btn_language.clicked.connect(self.toggle_language)
    
    def update_button_states(self):
        """Update button enabled/disabled states based on current state"""
        has_accounts = len(self.viewmodel.accounts) > 0
        is_processing = self.viewmodel.is_processing
        
        # Check if there are any accounts waiting for captcha
        has_captcha_pending = any(account.status == AccountStatus.CAPTCHA_PENDING 
                                for account in self.viewmodel.accounts)
        
        self.btn_import.setEnabled(not is_processing)
        self.btn_generate.setEnabled(not is_processing)
        self.btn_start.setEnabled(has_accounts and not is_processing)
        self.btn_pause.setEnabled(is_processing)
        self.btn_stop.setEnabled(is_processing)
        self.btn_export.setEnabled(has_accounts)
        self.btn_manual_captcha.setEnabled(has_captcha_pending and is_processing)
        
        # Update pause button text
        if self.viewmodel.is_paused:
            self.btn_pause.setText(tr("▶️ Resume"))
        else:
            self.btn_pause.setText(tr("⏸️ Pause"))
    
    def update_statistics(self):
        """Update the statistics display"""
        stats = self.viewmodel.statistics
        
        self.lbl_total.setText(str(stats['total']))
        self.lbl_success.setText(str(stats['success']))
        self.lbl_failed.setText(str(stats['failed']))
        self.lbl_remaining.setText(str(stats['remaining']))
        
        self.progress_bar.setValue(stats['progress'])
    
    def update_table(self):
        """Update the account table display"""
        accounts = self.viewmodel.accounts
        self.table_accounts.setRowCount(len(accounts))
        
        for row, account in enumerate(accounts):
            # Username with copy button
            username_widget = CopyableTextWidget(account.username, self.viewmodel)
            self.table_accounts.setCellWidget(row, 0, username_widget)
            
            # Password with visibility toggle and copy button
            password_widget = PasswordWidget(account.password, self.viewmodel)
            self.table_accounts.setCellWidget(row, 1, password_widget)
            
            # Status with icon and text
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(8, 4, 8, 4)
            status_layout.setSpacing(8)
            
            icon = StatusIcon(account.status)
            status_layout.addWidget(icon)
            
            status_text = QLabel(account.status.get_translated_name())
            status_colors = {
                AccountStatus.QUEUED: "#666666",
                AccountStatus.PROCESSING: "#0078D4",
                AccountStatus.CAPTCHA_PENDING: "#FFA500",  # Orange for waiting captcha
                AccountStatus.SUCCESS: "#107C10", 
                AccountStatus.FAILED: "#D83B01"
            }
            color = status_colors.get(account.status, "#000000")
            status_text.setStyleSheet(f"color: {color}; font-weight: bold;")
            status_layout.addWidget(status_text)
            status_layout.addStretch()
            
            self.table_accounts.setCellWidget(row, 2, status_widget)
            
            # Notes
            self.table_accounts.setItem(row, 3, QTableWidgetItem(account.notes))
    
    def log_message(self, message: str):
        """Add a message to the log output"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.txt_log.append(formatted_message)
        
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
        
        if file_path:
            success = self.viewmodel.import_accounts_from_csv(file_path)
            if success:
                QMessageBox.information(self, tr("Success"), 
                    tr("Imported %1 accounts successfully!").replace("%1", str(len(self.viewmodel.accounts))))
            else:
                QMessageBox.critical(self, tr("Error"), 
                    tr("Failed to import CSV file. Check the log for details."))
    
    def generate_accounts(self):
        """Generate random test accounts"""
        count, ok = QInputDialog.getInt(
            self, tr("Generate Accounts"), 
            tr("How many accounts to generate?"),
            10, 1, 1000
        )
        
        if ok:
            success = self.viewmodel.generate_random_accounts(count)
            if success:
                QMessageBox.information(self, tr("Success"), 
                    tr("Generated %1 accounts successfully!").replace("%1", str(count)))
            else:
                QMessageBox.critical(self, tr("Error"), 
                    tr("Failed to generate accounts. Check the log for details."))
    
    def start_processing(self):
        """Start the batch processing"""
        success = self.viewmodel.start_batch_processing()
        if not success:
            QMessageBox.warning(self, tr("Warning"), 
                tr("Cannot start processing. Check the log for details."))
    
    def pause_processing(self):
        """Pause or resume processing"""
        self.viewmodel.pause_batch_processing()
    
    def stop_processing(self):
        """Stop processing completely"""
        self.viewmodel.stop_batch_processing()
    
    def export_results(self):
        """Export results to CSV file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("Export Results"), 
            f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            tr("CSV Files (*.csv)")
        )
        
        if file_path:
            success = self.viewmodel.export_accounts_to_csv(file_path, include_results=True)
            if success:
                QMessageBox.information(self, tr("Success"), 
                    tr("Results exported successfully!\n\nFile: %1").replace("%1", os.path.basename(file_path)))
            else:
                QMessageBox.critical(self, tr("Error"), 
                    tr("Failed to export results. Check the log for details."))
    
    # Language related methods
    def update_language_button(self):
        """Update language button text based on current language"""
        self.btn_language.setText("🌐")
    
    def toggle_language(self):
        """Toggle between Chinese and English - delegated to ViewModel"""
        success = self.viewmodel.toggle_language()
        if not success:
            QMessageBox.warning(self, "Warning", "Failed to switch language")
    
    def manual_captcha_check(self):
        """Manual captcha check - delegated to ViewModel (MVVM View layer)"""
        # MVVM compliant: Only emit signal to ViewModel, no business logic
        success = self.viewmodel.manual_captcha_check()
        if not success:
            QMessageBox.information(self, tr("Information"), tr("No accounts are waiting for captcha completion"))
    
    def on_language_changed(self, new_locale: str):
        """Handle language change from ViewModel"""
        self.retranslate_ui(new_locale)
    
    def on_batch_complete(self, success_count: int, failed_count: int):
        """Handle batch processing completion"""
        QMessageBox.information(self, tr("Processing Complete"), 
            tr("Batch processing completed!\n\nSuccess: %1\nFailed: %2").replace("%1", str(success_count)).replace("%2", str(failed_count)))
    
    def on_captcha_detected(self, account, message: str):
        """Handle captcha detection from ViewModel (MVVM View layer)"""
        # Update UI display for captcha waiting status (响应ViewModel信号)
        self.update_accounts_display()
        
        # Show friendly captcha waiting prompt with multi-language support
        friendly_message = tr("🔍 CAPTCHA detected for %1. Please complete the captcha in the browser.\n"
                             "System will automatically check every 5 seconds.").replace("%1", account.username)
        self.log_message.emit(friendly_message)
        
        # Optional: Show system tray notification if available
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.showMessage(
                tr("Captcha Required"), 
                tr("Please complete captcha for %1").replace("%1", account.username),
                QSystemTrayIcon.Information, 5000
            )
    
    def on_captcha_resolved(self, account, message: str):
        """Handle captcha resolution from ViewModel (MVVM View layer)"""
        # Update UI display for successful captcha completion (响应ViewModel信号)
        self.update_accounts_display()
        
        # Show success message with multi-language support
        success_message = tr("🎉 CAPTCHA completed for %1! Continuing registration...").replace("%1", account.username)
        self.log_message.emit(success_message)
        
        # Optional: Show system tray notification if available
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.showMessage(
                tr("Captcha Completed"), 
                tr("Captcha completed for %1").replace("%1", account.username),
                QSystemTrayIcon.Information, 3000
            )
    
    def on_captcha_timeout(self, account, message: str):
        """Handle captcha timeout from ViewModel (MVVM View layer)"""
        # Update UI display for failed captcha timeout (响应ViewModel信号)
        self.update_accounts_display()
        
        # Show timeout warning with multi-language support
        timeout_message = tr("⏰ CAPTCHA timeout for %1 after 60 seconds. Account marked as failed.").replace("%1", account.username)
        self.log_message.emit(timeout_message)
        
        # Optional: Show system tray notification if available
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.showMessage(
                tr("Captcha Timeout"), 
                tr("Captcha timeout for %1").replace("%1", account.username),
                QSystemTrayIcon.Warning, 5000
            )
    
    def closeEvent(self, event):
        """Handle application close event"""
        self.viewmodel.cleanup()
        event.accept()


# Main Application Class
class BatchCreatorApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        
        # Application settings
        self.setApplicationName("360 Batch Account Creator")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("360 Tools")
        
        # Initialize translation system
        init_translation_manager(self)
        
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