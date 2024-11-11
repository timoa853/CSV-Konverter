Konvertiert CSV Dateien mit dem vorgegebenen Format - siehe Datei "BE-12345-24.csv" - in eine XML Datei mit dem Format OpenTrans 1.0

Die GUI.py (Graphical User Interface) ist das Frontend, welches ich mit dem TKinter erstellt habe.
In der main.py befindet sich der Code zu den eigentlichen Hauptfunktionen.
Mit setup.py kann man die GUI samt Funktionen auf sämtlichen Client-Rechnern abrufen und ausführen.

Artikel.txt und die Bestellnummer BE-12345-24.csv sind Beispieldateien für Testzwecke
batchfile.batch und VBS-file.vbs sorgen für das automatische Verschieben der CSV Datei in den Anzeige-Ordner der GUI.py

Die XML-Datei ist der Output, welcher dann in die Warenwirtschaft importiert werden kann, sofern das Warenwirtschaftsprogramm Format OpenTrans 1.0  importieren kann
