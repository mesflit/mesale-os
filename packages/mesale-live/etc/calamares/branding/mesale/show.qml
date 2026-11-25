import QtQuick 2.15
import calamares.slideshow 1.0
Presentation {
    id: p
    Timer { interval: 9000; running: p.activatedInCalamares; repeat: true; onTriggered: p.goToNextSlide() }
    component Kare: Slide {
        property string gorsel; property string baslik; property string yazi
        anchors.fill: parent
        Image { anchors.fill: parent; source: "file:///usr/share/mesale/previews/" + gorsel; fillMode: Image.PreserveAspectCrop; smooth: true }
        Rectangle { anchors.centerIn: parent; width: parent.width * 0.7; height: 130; radius: 26; color: "#c8ffffff"
            Column { anchors.centerIn: parent; spacing: 10; width: parent.width - 48
                Text { text: baslik; color: "#16243d"; font.pixelSize: 26; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
                Text { text: yazi; color: "#3b4d6d"; font.pixelSize: 15; width: parent.width; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter } } }
    }
    Kare { gorsel: "day.png"; baslik: "Welcome to Mesale OS"; yazi: "A solid Debian base with the newest kernel, drivers and GNOME." }
    Kare { gorsel: "dusk.png"; baslik: "Super + Space"; yazi: "Command bar: launch, switch, calculate, install." }
    Kare { gorsel: "dawn.png"; baslik: "Mesale Center"; yazi: "Look and features in one place." }
    Kare { gorsel: "night.png"; baslik: "Your choice"; yazi: "Only what you picked gets installed." }
}
