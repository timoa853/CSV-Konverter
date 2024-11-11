@echo off
set "source=C:\your\reading-folder\export"
set "destination=C:\your\destination-folder\export"

echo Quellordner: %source%
echo Zielordner: %destination%

:: Testen, ob Quellordner existiert
if not exist "%source%" (
    echo Der Quellordner wurde nicht gefunden!
    exit /b
)

:: Testen, ob Zielordner existiert
if not exist "%destination%" (
    echo Der Zielordner wurde nicht gefunden!
    exit /b
)

:: Anzeigen der Dateien im Quellordner
echo Dateien im Quellordner:
dir "%source%\*.csv"

:: Dateien verschieben
move /Y "%source%\*.csv" "%destination%"

:: Überprüfen, ob der Befehl erfolgreich war
if %errorlevel% neq 0 (
    echo Fehler beim Verschieben der Dateien!
) else (
    echo Dateien wurden erfolgreich verschoben.
)

:: Anzeigen der Dateien im Zielordner
echo Dateien im Zielordner:
dir "%destination%\*.csv"
