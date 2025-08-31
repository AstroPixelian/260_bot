#!/usr/bin/env python3
"""
Translation Manager for 360 Batch Account Creator
Handles language switching and translation loading.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from PySide6.QtCore import QObject, Signal, QTranslator, QCoreApplication, QLocale, QSettings
from PySide6.QtWidgets import QApplication


class TranslationManager(QObject):
    """Manages application translations and language switching"""
    
    # Signal emitted when language changes
    languageChanged = Signal(str)  # locale code
    
    def __init__(self, app: QApplication, parent=None):
        super().__init__(parent)
        self.app = app
        self.settings = QSettings()
        
        # Available languages
        self.available_languages = {
            'en-US': {'name': 'English', 'display_name': 'English'},
            'zh-CN': {'name': 'Chinese', 'display_name': '中文'}
        }
        
        # Current translator
        self.current_translator: Optional[QTranslator] = None
        self.current_locale = 'en-US'  # Default
        
        # Translation files directory
        self.translations_dir = Path(__file__).parent.parent / 'i18n'
        
    def get_available_languages(self) -> Dict[str, Dict[str, str]]:
        """Get available languages dictionary"""
        return self.available_languages.copy()
    
    def get_current_locale(self) -> str:
        """Get current locale code"""
        return self.current_locale
    
    def get_system_locale(self) -> str:
        """Get system default locale, fallback to en-US"""
        system_locale = QLocale.system().name()
        
        # Check if system locale is available
        if system_locale in self.available_languages:
            return system_locale
        
        # Try language part only (e.g., 'zh' from 'zh-TW')
        language_code = system_locale.split('-')[0]
        for locale in self.available_languages:
            if locale.startswith(language_code):
                return locale
        
        # Fallback to English
        return 'en-US'
    
    def load_saved_language(self) -> str:
        """Load language from settings, fallback to system locale"""
        saved_locale = self.settings.value('language', self.get_system_locale())
        
        # Validate saved locale
        if saved_locale in self.available_languages:
            return saved_locale
        
        return self.get_system_locale()
    
    def save_language(self, locale: str) -> None:
        """Save language preference to settings"""
        if locale in self.available_languages:
            self.settings.setValue('language', locale)
    
    def switch_language(self, locale: str) -> bool:
        """
        Switch to specified language.
        
        Args:
            locale: Language locale code (e.g., 'zh-CN', 'en-US')
            
        Returns:
            True if language switch was successful, False otherwise
        """
        if locale not in self.available_languages:
            print(f"Warning: Language '{locale}' not available")
            return False
        
        if locale == self.current_locale:
            return True  # Already using this language
        
        # Remove current translator if exists
        if self.current_translator:
            self.app.removeTranslator(self.current_translator)
            self.current_translator = None
        
        # Don't load translator for English (source language)
        if locale == 'en-US':
            self.current_locale = locale
            self.save_language(locale)
            self.languageChanged.emit(locale)
            return True
        
        # Load new translation file
        translation_file = self.translations_dir / f"{locale}.qm"
        
        # If .qm file doesn't exist, try to find .ts file and warn user
        if not translation_file.exists():
            ts_file = self.translations_dir / f"{locale}.ts"
            if ts_file.exists():
                print(f"Warning: Translation file {translation_file} not found.")
                print(f"Found {ts_file}. You need to compile it using:")
                print(f"pyside6-lrelease {ts_file} -qm {translation_file}")
                
                # Try to compile automatically
                try:
                    import subprocess
                    result = subprocess.run([
                        'pyside6-lrelease', str(ts_file), '-qm', str(translation_file)
                    ], capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print(f"Successfully compiled {translation_file}")
                    else:
                        print(f"Failed to compile translation: {result.stderr}")
                        return False
                        
                except Exception as e:
                    print(f"Could not auto-compile translation: {e}")
                    return False
            else:
                print(f"Error: Neither .qm nor .ts file found for locale '{locale}'")
                return False
        
        # Create and load translator
        translator = QTranslator(self)
        
        if translator.load(str(translation_file)):
            self.app.installTranslator(translator)
            self.current_translator = translator
            self.current_locale = locale
            self.save_language(locale)
            
            # Emit signal to notify UI components
            self.languageChanged.emit(locale)
            
            print(f"Successfully switched to language: {locale}")
            return True
        else:
            print(f"Failed to load translation file: {translation_file}")
            return False
    
    def initialize_language(self) -> None:
        """Initialize language on application startup"""
        saved_locale = self.load_saved_language()
        self.switch_language(saved_locale)
    
    def get_language_display_name(self, locale: str) -> str:
        """Get display name for language"""
        return self.available_languages.get(locale, {}).get('display_name', locale)


# Global instance holder
_translation_manager_instance: Optional[TranslationManager] = None


def get_translation_manager() -> Optional[TranslationManager]:
    """Get global translation manager instance"""
    return _translation_manager_instance


def init_translation_manager(app: QApplication) -> TranslationManager:
    """Initialize global translation manager instance"""
    global _translation_manager_instance
    if _translation_manager_instance is None:
        _translation_manager_instance = TranslationManager(app)
    return _translation_manager_instance


def tr(text: str, context: str = "BatchCreatorMainWindow") -> str:
    """
    Convenient translation function.
    
    Args:
        text: Text to translate
        context: Translation context (default: BatchCreatorMainWindow)
        
    Returns:
        Translated text
    """
    return QCoreApplication.translate(context, text)