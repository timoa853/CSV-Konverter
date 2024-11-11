import customtkinter
from PIL import Image
from tkinter import messagebox, ttk
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
from main import CSVFileHandler
import shutil
import os
from tkinterdnd2 import TkinterDnD
from collections import namedtuple



class FolderEventHandler(FileSystemEventHandler):
    """Event-Handler, der Änderungen im Ordner überwacht und den Inhalt neu lädt."""
    def __init__(self, app):
        self.app = app

    def on_modified(self, event):
        self.app.load_folder_content()

    def on_created(self, event):
        self.app.load_folder_content()

    def on_deleted(self, event):
        self.app.load_folder_content()


class DnDCTkTextbox(customtkinter.CTkTextbox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class App:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("CSV Verarbeitungs Tool")
        self.root.geometry("900x800")
        self.root.resizable(False, False)

        self.observer = None
        self.is_running = False
        self.directory_to_watch = r"\your\destination-folder\CSV-file"  # Zielordner
        self.directory_to_indicate = r"\your\displayed-folder\CSV-file"  # Angezeigter Ordner

        self.dragged_file_path = None  # Variable, um den Pfad der gezogenen Datei zu speichern

        self.create_background()
        self.create_widgets()
        self.start_folder_observer()  # Startet den Ordnerbeobachter für Echtzeitaktualisierung

    def create_background(self):
        self.bg_image = customtkinter.CTkImage(Image.open("img/gradient.png"), size=(900, 800))
        self.bg_label = customtkinter.CTkLabel(self.root, image=self.bg_image, text="")
        self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    def create_widgets(self):
        # Logos
        self.dc_logo = customtkinter.CTkImage(Image.open("img/DC_Logo.png"), size=(100, 50))
        self.sp_logo = customtkinter.CTkImage(Image.open("img/Spiel_Preis.png"), size=(100, 50))

        logo_frame = customtkinter.CTkFrame(self.root, fg_color="black")
        logo_frame.pack(pady=20)

        dc_logo_label = customtkinter.CTkLabel(logo_frame, image=self.dc_logo, text="")
        dc_logo_label.pack(side="left", padx=10)

        sp_logo_label = customtkinter.CTkLabel(logo_frame, image=self.sp_logo, text="")
        sp_logo_label.pack(side="left", padx=10)

        # Titel
        self.label = customtkinter.CTkLabel(self.root, text="DINO CARS - Lexware Import",
                                            font=("Arial", 16, "bold"), text_color="white", fg_color="black")
        self.label.pack(pady=20)

        # Treeview für Ordneransicht
        self.tree_frame = customtkinter.CTkFrame(self.root, fg_color="black", width=500, height=200)
        self.tree_frame.pack(pady=20, padx=10)
        self.tree_frame.pack_propagate(False)  # Verhindert, dass der Frame sich an den Inhalt anpasst

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background="#1e1e1e",
                        foreground="white",
                        fieldbackground="#1e1e1e",
                        borderwidth=0)
        style.map('Treeview', background=[('selected', '#858282')])

        style.configure("Treeview.Heading",
                        background="#1e1e1e",
                        foreground="white",
                        relief="flat")
        style.map("Treeview.Heading",
                  background=[('active', '#858282')])

        self.tree = ttk.Treeview(self.tree_frame, columns=("Name"), show='headings', selectmode='extended')
        self.tree.heading("Name", text="Bitte Dateien markieren und Verschieben-Button drücken")
        self.tree.column("Name", width=250)
        self.tree.pack(fill='both', expand=True)

        # Scrollbar hinzufügen
        scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Dateien im Ordner anzeigen
        self.load_folder_content()


        # Frame für Buttons und Status-Label
        control_frame = customtkinter.CTkFrame(self.root, fg_color="black")
        control_frame.pack(side="bottom", pady=40)

        # Button-Frame
        button_frame = customtkinter.CTkFrame(control_frame, fg_color="black")
        button_frame.pack()

        # Start-Button
        self.start_button = customtkinter.CTkButton(button_frame, text="Starten", command=self.start_watchdog,
                                                    width=120, height=32, fg_color="#4CAF50", hover_color="#45a049")
        self.start_button.pack(side="left", padx=10)

        # Verschieben-Button
        self.move_button = customtkinter.CTkButton(button_frame, text="Verschieben", command=self.move_selected_files,
                                                   width=120, height=32, fg_color="#07b8e0", hover_color="#049bbd")
        self.move_button.pack(side="left", padx=10)

        # Stop-Button
        self.stop_button = customtkinter.CTkButton(button_frame, text="Beenden", command=self.stop_watchdog,
                                                   width=120, height=32, fg_color="#f44336", hover_color="#d32f2f")
        self.stop_button.pack(side="left", padx=10)

        # Status-Label
        self.status_label = customtkinter.CTkLabel(control_frame, text="Bereit",
                                                   font=("Arial", 15, "italic"), text_color="#666666", fg_color="black")
        self.status_label.pack(pady=10)

    def load_folder_content(self):
        """Lädt den Inhalt des Ordners in das Treeview-Widget."""
        # Löscht vorhandene Einträge im Treeview
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Durchläuft den Ordner und fügt Dateien zum Treeview hinzu
        for file_name in os.listdir(self.directory_to_indicate):
            file_path = os.path.join(self.directory_to_indicate, file_name)
            file_type = "Datei" if os.path.isfile(file_path) else "Ordner"
            self.tree.insert('', 'end', values=(file_name,))

    def move_selected_files(self):
        """Verschiebt die markierten Dateien in den Zielordner und verarbeitet sie."""
        # Überprüfen, ob der Dateileser läuft
        if not self.is_running:
            messagebox.showerror("Fehler", "Drücke erst den Starten-Button, um die Datei verschieben zu können.")
            return

        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warnung", "Keine Datei ausgewählt")
            return

        csv_handler = CSVFileHandler()
        FileEvent = namedtuple('FileEvent', ['src_path'])

        for item_id in selected_items:
            file_name = self.tree.item(item_id, 'values')[0]
            source_path = os.path.join(self.directory_to_indicate, file_name)
            destination_path = os.path.join(self.directory_to_watch, file_name)

            try:
                shutil.move(source_path, destination_path)
                self.status_label.configure(text=f"Datei {file_name} verschoben", text_color="#4CAF50")

                # Erstelle ein FileEvent-Objekt und übergebe es an on_created
                file_event = FileEvent(src_path=destination_path)
                csv_handler.on_created(file_event)

            except Exception as e:
                self.status_label.configure(text=f"Fehler beim Verschieben/Verarbeiten: {str(e)}", text_color="#f44336")

        # Aktualisiere die Ordneransicht nach dem Verschieben
        self.load_folder_content()

    def start_folder_observer(self):
        """Startet den Observer für den angezeigten Ordner, um Änderungen in Echtzeit anzuzeigen."""
        event_handler = FolderEventHandler(self)
        self.folder_observer = Observer()
        self.folder_observer.schedule(event_handler, self.directory_to_indicate, recursive=False)
        self.folder_observer.start()

    def stop_folder_observer(self):
        """Beendet den Folder-Observer, der die Ordner-Änderungen überwacht."""
        if self.folder_observer:
            self.folder_observer.stop()
            self.folder_observer.join()

    def start_watchdog(self):
        if self.is_running:
            messagebox.showinfo("Info", "Der Prozess läuft bereits.")
            return

        try:
            self.is_running = True
            self.observer = Observer()
            event_handler = CSVFileHandler()
            self.observer.schedule(event_handler, path=self.directory_to_watch, recursive=False)
            self.observer_thread = threading.Thread(target=self.observer.start)
            self.observer_thread.start()
            self.status_label.configure(text="Ordnerleser läuft", text_color="#4CAF50")

        except Exception as e:
            self.is_running = False
            self.status_label.configure(text="Fehler beim Starten", text_color="#f44336")
            messagebox.showerror("Fehler", f"Ordnerleser konnte nicht gestartet werden: {str(e)}")

    def stop_watchdog(self):
        if not self.is_running:
            return

        try:
            self.observer.stop()
            self.observer.join()
            self.is_running = False
            self.status_label.configure(text="Ordnerleser gestoppt", text_color="#f44336")
        except Exception as e:
            self.status_label.configure(text="Fehler beim Stoppen", text_color="#f44336")
            messagebox.showerror("Fehler", f"Fehler beim Stoppen des Ordnerlesers: {str(e)}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    customtkinter.set_appearance_mode("dark")
    customtkinter.set_default_color_theme("dark-blue")
    app = App()
    app.run()
