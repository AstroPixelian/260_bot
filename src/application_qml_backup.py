# Copyright
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import sys

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine


class AccountBatchCreatorApp(QGuiApplication):
    """
    Main application class for 360 Account Batch Creator
    Simplified version focused on the core functionality
    """

    def __init__(self, args):
        super().__init__(args)
        self._engine = QQmlApplicationEngine()

    def set_window_icon(self):
        """Set the application window icon"""
        icon = QIcon(":/data/app-icon.svg")
        self.setWindowIcon(icon)

    def set_up_signals(self):
        """Set up application signals"""
        self.aboutToQuit.connect(self._on_quit)

    def _on_quit(self) -> None:
        """Clean up when application is about to quit"""
        del self._engine

    def start_engine(self):
        """Start the QML engine and load the main QML file"""
        self._engine.load(QUrl.fromLocalFile(":/qt/qml/main.qml"))

    def verify(self):
        """Verify that the application started correctly"""
        if not self._engine.rootObjects():
            sys.exit(-1)