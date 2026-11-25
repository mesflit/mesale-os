import QtQuick 2.15
import calamares.slideshow 1.0

Presentation {
    id: presentation

    Timer {
        interval: 9000
        repeat: true
        running: presentation.activatedInCalamares
        onTriggered: presentation.goToNextSlide()
    }

    component Page: Slide {
        property string picture
        property string heading
        property string body

        anchors.fill: parent

        Image {
            anchors.fill: parent
            source: "file:///usr/share/mesale/previews/" + picture
            fillMode: Image.PreserveAspectCrop
        }
        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.7
            height: 130
            radius: 26
            color: "#c8ffffff"

            Column {
                anchors.centerIn: parent
                width: parent.width - 48
                spacing: 10

                Text {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: heading
                    color: "#16243d"
                    font { pixelSize: 26; bold: true }
                }
                Text {
                    width: parent.width
                    text: body
                    color: "#3b4d6d"
                    font.pixelSize: 15
                    wrapMode: Text.WordWrap
                    horizontalAlignment: Text.AlignHCenter
                }
            }
        }
    }

    Page { picture: "day.png"; heading: "Welcome to Mesale OS"; body: "A Debian base with the newest kernel, drivers and GNOME." }
    Page { picture: "dusk.png"; heading: "Super + Space"; body: "Command bar: launch, switch, calculate, install." }
    Page { picture: "dawn.png"; heading: "Mesale Center"; body: "Look and features in one place." }
    Page { picture: "night.png"; heading: "Your choice"; body: "Only what you picked gets installed." }
}
