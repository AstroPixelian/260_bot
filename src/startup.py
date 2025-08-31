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


import os
import sys


class StartUp:
    """Necessary steps for environment, Python and Qt"""

    @staticmethod
    def configure_qt_application_data():
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.setApplicationName("360 Account Batch Creator")
        QCoreApplication.setOrganizationName("360 Tools")
        QCoreApplication.setApplicationVersion("1.0.0")

    @staticmethod
    def configure_environment_variables():
        # No special environment configuration needed for this simple app
        pass

    @staticmethod
    def import_bindings():
        # No special Python object bindings needed yet
        pass

    @staticmethod
    def start_application():
        from src.application import AccountBatchCreatorApp
        app = AccountBatchCreatorApp(sys.argv)

        app.set_window_icon()
        app.set_up_signals()
        app.start_engine()
        app.verify()

        sys.exit(app.exec())


def perform_startup():
    we = StartUp()

    we.configure_qt_application_data()
    we.configure_environment_variables()
    we.import_bindings()

    we.start_application()
