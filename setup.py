#Set-Up Datei für GUI-Datei



from cx_Freeze import setup, Executable
import os

# Ermitteln Sie den Pfad zu customtkinter
import customtkinter
customtkinter_path = os.path.dirname(customtkinter.__file__)

# Definieren Sie zusätzliche Dateien und Pakete
additional_files = [
    (customtkinter_path, "customtkinter"),
    ("img", "img"),
    ("C:\\Windows\\System32\\VCRUNTIME140_1.dll", "VCRUNTIME140_1.dll")
]

build_exe_options = {
    "packages": ["customtkinter", "PIL", "tkinter", "watchdog", "threading", "os"],
    "include_files": additional_files,
    "include_msvcr": True,
}

# Definiere die Python-Datei, die als Executable kompiliert werden soll
executables = [Executable("GUI.py", base="Win32GUI", icon="Leximport.ico")]

# Erstelle die Setup-Konfiguration
setup(
    name="Lex-Bestellimport",
    version="1.1",
    description="Lex-Bestellimport OpenTrans 1.0",
    options={"build_exe": build_exe_options},
    executables=executables
)
