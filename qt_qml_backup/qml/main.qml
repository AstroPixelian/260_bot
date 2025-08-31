/*
Copyright

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    
    width: 1200
    height: 800
    visible: true
    title: "360 Account Batch Creator v1.0"
    
    // Main content area
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 20
        spacing: 20
        
        // Title and controls row
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            
            Text {
                text: "360 Account Batch Creator"
                font.pointSize: 18
                font.bold: true
            }
            
            Item { Layout.fillWidth: true } // Spacer
            
            Button {
                text: "Import CSV"
                onClicked: {
                    // TODO: Implement CSV import functionality
                }
            }
            
            Button {
                text: "Start"
                enabled: false // Will be enabled when accounts are loaded
                onClicked: {
                    // TODO: Implement start functionality
                }
            }
            
            Button {
                text: "Pause"
                enabled: false
                onClicked: {
                    // TODO: Implement pause functionality
                }
            }
            
            Button {
                text: "Stop"
                enabled: false
                onClicked: {
                    // TODO: Implement stop functionality
                }
            }
            
            Button {
                text: "Export Results"
                onClicked: {
                    // TODO: Implement export functionality
                }
            }
        }
        
        // Progress section
        RowLayout {
            Layout.fillWidth: true
            spacing: 20
            
            Text {
                text: "Progress: 0%"
                font.pointSize: 12
            }
            
            Text {
                text: "Total: 0 | Success: 0 | Failed: 0"
                font.pointSize: 12
            }
        }
        
        // Accounts table (placeholder)
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            border.color: "#cccccc"
            border.width: 1
            
            Text {
                anchors.centerIn: parent
                text: "Account list will be displayed here"
                color: "#666666"
            }
        }
        
        // Log section
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 150
            border.color: "#cccccc"
            border.width: 1
            
            ScrollView {
                anchors.fill: parent
                anchors.margins: 5
                
                TextArea {
                    placeholderText: "Application logs will appear here..."
                    readOnly: true
                    wrapMode: TextArea.Wrap
                }
            }
        }
    }
}