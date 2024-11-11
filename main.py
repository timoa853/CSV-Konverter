from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import pandas as pd
from datetime import datetime, timedelta
import time
import os


class CSVFileHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.artikel_file_path = r"U:\Auswertung\artikel.txt"
        self.artikel_df = self.load_artikel_data(self.artikel_file_path)

    def load_artikel_data(self, file_path):
        # Einlesen der Textdatei, separiert durch ";"
        df_artikel = pd.read_csv(file_path, sep=";", dtype=str, encoding="ansi")
        # Bereinigen und Konvertieren der 'Preis 1'-Spalte
        df_artikel['Preis 1'] = df_artikel['Preis 1'].str.replace(',', '.').str.replace('€', '').str.strip()
        df_artikel['Preis 1'] = pd.to_numeric(df_artikel['Preis 1'], errors='coerce')
        # Konvertiere 'Artikelnummer' zu String
        df_artikel['Artikelnummer'] = df_artikel['Artikelnummer'].astype(str)
        df_artikel['Bezeichnung'] = df_artikel['Bezeichnung'].astype(str)
        return df_artikel  # Gib den DataFrame zurück

    def on_created(self, event):
        if event.src_path.endswith(".csv"):
            print(f"Neue CSV-Datei erkannt: {event.src_path}")
            self.process_csv_with_retry(event.src_path)

    def process_csv_with_retry(self, file_path, max_retries=5, delay=1):
        for attempt in range(max_retries):
            try:
                time.sleep(delay)  # Warten Sie vor jedem Versuch
                self.process_csv(file_path)
                break  # Wenn erfolgreich, beenden Sie die Schleife
            except Exception as e:
                print(f"Versuch {attempt + 1} fehlgeschlagen: {str(e)}")
                if attempt == max_retries - 1:
                    print(f"Konnte die Datei nach {max_retries} Versuchen nicht verarbeiten.")

    def check_and_modify_product_id(self, product_id):
        # Prüfen auf NaN-Werte
        if pd.isna(product_id):
            print(f"Product ID is NaN, replacing with '0'")
            return '0'

        # Konvertieren zu String
        product_id = str(product_id)
        artikelnummer_list = self.artikel_df['Artikelnummer'].values

        if product_id not in artikelnummer_list:
            print(f"Product ID {product_id} not found in article list, adding '0'")
            product_id_with_zero = '0' + product_id

            # Prüfen, ob die Artikelnummer mit vorangestellter '0' existiert
            if product_id_with_zero in artikelnummer_list:
                return product_id_with_zero
            else:
                # Wenn die Artikelnummer nicht existiert, abbrechen oder Standardwert zurückgeben
                print(f"Product ID {product_id_with_zero} still not found after adding '0'.")
                return product_id  # Behalte die ursprüngliche ID bei

        return product_id

    def process_csv(self, file_path):
        # CSV wird in einem Pandas DataFrame umgewandelt, bei PhoneNo. als String, um führende Nullen zu erhalten
        df = pd.read_csv(file_path, sep=",",
                         dtype={'Quantity': int, 'ProductId': str, 'ReferenceNo': str, 'PhoneNo.': str})

        # Einlesen des Verfüg_xls Arbeitsblatts
        verfug_df = pd.read_excel(r"U:\PREISLISTEN\2024\PREISLISTE DINO CARS 2024 - Master.xlsx",
                                  sheet_name="Verfüg_xls")

        # Vorprüfung auf "DINO" im 'ProductId'
        df['ProductId'] = df['ProductId'].apply(lambda x: x if "DINO" in x else (x + " DINO"))

        # Prüfen und ggf. "0" hinzufügen
        df['ProductId'] = df['ProductId'].apply(self.check_and_modify_product_id)

        # Zusammenführen von df und artikel_df, um 'Preis 1' und 'Bezeichnung' zu erhalten
        df = pd.merge(df, self.artikel_df[['Artikelnummer', 'Preis 1', 'Bezeichnung']], how='left', left_on='ProductId',
                      right_on='Artikelnummer')

        # Fehlende Preise auffüllen
        df['Preis 1'] = df['Preis 1'].fillna(0.00)

        # Gruppieren nach ReferenceNo
        grouped = df.groupby('ReferenceNo')

        new_rows = []
        for reference_no, group in grouped:
            line_item_id = 1  # Initialisierung der Line Item ID

            # Logik für 99999 Artikel
            fbs_bf3_count = group[group['ProductId'].str.contains('FBS BF3 DINO')]['Quantity'].sum()
            sb6_count = group[group['ProductId'].str.startswith('SB 6')]['Quantity'].sum()
            diff = fbs_bf3_count - sb6_count

            if diff > 0:
                preis_99999 = self.artikel_df.loc[self.artikel_df['Artikelnummer'] == '99999', 'Preis 1'].values
                preis = preis_99999[0] if len(preis_99999) > 0 else 0.00
                new_row = pd.DataFrame({
                    'ReferenceNo': [reference_no] * diff,
                    'ProductId': ['99999'] * diff,
                    'Quantity': [1] * diff,
                    'Artikelnummer': ['99999'] * diff,
                    'Preis 1': [preis] * diff,
                    'LineItemID': [line_item_id] * diff  # Line Item ID für 99999
                })
                new_rows.append(new_row)
                line_item_id += 1

            # Logik für LT00000 DINO für alle anderen Artikel außer '99999'
            for _, row in group.iterrows():
                row_dict = row.to_dict()
                row_dict['LineItemID'] = line_item_id  # Line Item ID für die Hauptposition
                new_rows.append(row_dict)
                line_item_id += 1

                if row['ProductId'] != '99999':  # LT00000 nur für Nicht-99999-Artikel hinzufügen
                    verfug_row = verfug_df[verfug_df['DINO_INTERN'] == row['ProductId']]

                    if not verfug_row.empty:
                        artikel_article = verfug_row['ARTIKEL_ARTICLE'].values[0]
                        datum_date = verfug_row['DATUM_DATE'].values[0]

                        if pd.isnull(datum_date) or datum_date == 0:
                            datum = (datetime.now() + timedelta(days=3)).isocalendar()[1]  # KW + 3 Tage
                        else:
                            datum = (pd.to_datetime(datum_date) + timedelta(days=3)).isocalendar()[
                                1]  # Vfgbarkeitstermin + 3Tage Bearbeitungs und Lieferzeit

                        artikel_bezeichnung = f" Lieferung in KW {datum}"
                    else:
                        artikel_bezeichnung = "Bitte Liefertermin hinzufügen"
                        datum = (datetime.now() + timedelta(days=5)).isocalendar()[1]

                    # Füge LT00000 DINO direkt nach der Bestellposition hinzu
                    new_row = {
                        'ReferenceNo': reference_no,
                        'ProductId': 'LT00000 DINO',
                        'Quantity': 1,
                        'Preis 1': 0.00,
                        'Artikelbezeichnung': artikel_bezeichnung,
                        'Liefertermin': f"Lieferung in KW {datum}",
                        'LineItemID': line_item_id  # Line Item ID für LT00000 DINO
                    }
                    new_rows.append(new_row)
                    line_item_id += 1  # Erhöhe die Line Item ID

        # Alle neuen Zeilen zum Hauptdataframe hinzufügen
        df = pd.DataFrame(new_rows)  # Liste in DataFrame umwandeln

        def generate_order_block(group):
            # ZipCode und PhoneNo. als Strings behandeln, um das Anhängen von .0 zu verhindern
            def format_zipcode(zipcode, country_id):
                if pd.notna(zipcode):
                    zipcode = str(int(zipcode))  # Als String behandeln
                    if len(zipcode) == 4 and country_id in ['DE', 'DEU']:
                        return '0' + zipcode  # Füge führende 0 hinzu, wenn 4-stellig und CountryId 'DE' oder 'DEU'
                return zipcode

            group['ZipCode'] = group.apply(lambda x: format_zipcode(x['ZipCode'], x['CountryId']), axis=1)

            # PhoneNo. prüfen und korrekt formatieren (entweder mit "0", "00" oder unverändert)
            def format_phone_no(phone):
                if pd.isna(phone):
                    return ''

                phone_str = str(phone).strip()

                if phone_str.startswith("+"):
                    return phone_str.replace("+", "00")

                if phone_str.startswith("00"):
                    return phone_str

                if not phone_str.startswith("0"):
                    return "0" + phone_str

                return phone_str

            group['PhoneNo.'] = group['PhoneNo.'].apply(format_phone_no)

            # Leere NaN-Werte in den anderen Feldern durch leere Strings ersetzen
            group[['CompanyName', 'Surname', 'FirstName', 'Address', 'City', 'CountryId', 'Email']] = group[
                ['CompanyName', 'Surname', 'FirstName', 'Address', 'City', 'CountryId', 'Email']].fillna('')

            # Erstelle den ORDER_HEADER einmal pro Bestellung
            order_header = f"""
            <ORDER xmlns="http://www.opentrans.org/XMLSchema/1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0" type="standard">
            <ORDER_HEADER>
                <CONTROL_INFO>
                    <GENERATOR_INFO>Shop 2.0</GENERATOR_INFO>
                    <GENERATION_DATE>{datetime.now().isoformat()}</GENERATION_DATE>
                </CONTROL_INFO>
                <ORDER_INFO>
                     <REMARK type = "order">Kontakt: E-Mail= {group['Email'].iloc[0]} Tel= {group['PhoneNo.'].iloc[0]}</REMARK>
                     <REMARK type = "delivery_method">Delivery DAP</REMARK>
                     <REMARK type = "shipping_fee">0</REMARK>
                    <ORDER_ID>{group['ReferenceNo'].iloc[0]}</ORDER_ID>
                    <ORDER_DATE>{datetime.now().isoformat()}</ORDER_DATE>
                    <ORDER_PARTIES>
                        <BUYER_PARTY>
                            <PARTY>
                                <ADDRESS>
                                    <NAME>{group['CompanyName'].iloc[0] if group['CompanyName'].iloc[0] else ''}</NAME>
                                    <NAME2>{group['Surname'].iloc[0] if group['Surname'].iloc[0] else ''}</NAME2>
                                    <NAME3>{group['FirstName'].iloc[0] if group['FirstName'].iloc[0] else ''}</NAME3>
                                    <STREET>{group['Address'].iloc[0]}</STREET>
                                    <ZIP>{group['ZipCode'].iloc[0]}</ZIP>
                                    <CITY>{group['City'].iloc[0]}</CITY>
                                    <COUNTRY>{group['CountryId'].iloc[0]}</COUNTRY>
                                    <PHONE type="other">{group['PhoneNo.'].iloc[0]}</PHONE>
                                    <EMAIL>{group['Email'].iloc[0]}</EMAIL>
                                </ADDRESS>
                            </PARTY>
                        </BUYER_PARTY>
                        <INVOICE_PARTY>
                            <PARTY>
                                <ADDRESS>
                                    <NAME>SPIEL-PREIS GmbH &amp; Co. KG</NAME>
                                    <NAME2>SCHWANEWEDE</NAME2>
                                    <NAME3>INGE</NAME3>
                                    <STREET>AM BREITENSTOCK 8</STREET>
                                    <ZIP>90559</ZIP>
                                    <CITY>BURGTHANN/EZELSDORF</CITY>
                                    <COUNTRY>DE</COUNTRY>
                                    <PHONE type="other">09188 / 99 99 00</PHONE>
                                    <EMAIL>presales@spiel-preis.de</EMAIL>
                                </ADDRESS>
                            </PARTY>
                        </INVOICE_PARTY>
                    </ORDER_PARTIES>
                </ORDER_INFO>
            </ORDER_HEADER>"""

            group = group.drop(
                columns=['ReferenceNo', 'CompanyName', 'Surname', 'FirstName', 'Address', 'ZipCode', 'City',
                         'CountryId', 'PhoneNo.', 'Email', 'Artikelnummer'])

            # Erstelle die ORDER_ITEM_LIST für alle Artikel dieser Bestellung
            order_item_list = "<ORDER_ITEM_LIST>\n"
            for idx, row in group.iterrows():
                price = float(row['Preis 1']) * (1 - 0.34)  # Rabattierter Preis
                quantity = float(row['Quantity'])  # Menge

                # Formatiere den Einzelpreis und berechne den Gesamtpreis
                price_formatted = f"{price:.2f}"
                total_price = price * quantity
                total_price_formatted = f"{total_price:.2f}"

                # Prüfen, ob es sich um den speziellen Artikel "99999" oder "LT00000 DINO" handelt
                if row['ProductId'] == '99999':
                    artikel_name = "ACHTUNG!!!! Style-Box und Frame Box passen nicht zueinander"
                elif row['ProductId'] == 'LT00000 DINO':
                    artikel_name = row['Artikelbezeichnung']
                else:
                    # Für andere Artikel die Bezeichnung aus der artikel.txt Datei verwenden
                    artikel_name = \
                        self.artikel_df.loc[self.artikel_df['Artikelnummer'] == row['ProductId'], 'Bezeichnung'].values[
                            0] \
                            if row['ProductId'] in self.artikel_df[
                            'Artikelnummer'].values else "Artikelbezeichnung nicht verfügbar"

                order_item_list += f"""
                <ORDER_ITEM>
                    <LINE_ITEM_ID>{idx + 1}</LINE_ITEM_ID>
                    <ARTICLE_ID>
                        <SUPPLIER_AID>{row['ProductId']}</SUPPLIER_AID>
                        <DESCRIPTION_SHORT>{artikel_name}</DESCRIPTION_SHORT>
                    </ARTICLE_ID>
                    <QUANTITY>{row['Quantity']}</QUANTITY>
                    <ORDER_UNIT>1</ORDER_UNIT>
                    <ARTICLE_PRICE>
                        <PRICE_AMOUNT>{price_formatted}</PRICE_AMOUNT>
                        <PRICE_LINE_AMOUNT>{total_price_formatted}</PRICE_LINE_AMOUNT>
                        <PRICE_CURRENCY>EUR</PRICE_CURRENCY>
                    </ARTICLE_PRICE>
                </ORDER_ITEM>"""

            order_item_list += "\n</ORDER_ITEM_LIST>\n</ORDER>"

            return order_header + order_item_list

        # Generiere XML-Daten
        grouped = df.groupby("ReferenceNo")
        xml_output = (
                '<?xml version="1.0" encoding="ISO-8859-1"?>\n<ORDER_LIST>\n'
                + "\n".join(grouped.apply(generate_order_block))
                + "\n</ORDER_LIST>"
        )

        # Pfad zum Ordner, in dem die XML-Datei gespeichert werden soll
        output_folder = r"U:\Workflows\Bestellimport\Spiel_Preis\XML_Output"
        os.makedirs(output_folder, exist_ok=True)

        # Bestimme den Namen der Ausgabedatei
        output_filename = os.path.join(output_folder, f"{os.path.basename(file_path).replace('.csv', '')}.xml")

        # Schreibe die XML-Daten in die Datei
        with open(output_filename, "w", encoding="ISO-8859-1") as xml_file:
            xml_file.write(xml_output)


if __name__ == "__main__":
    path = r"U:\Workflows\Bestellimport\Spiel_Preis\CSV_Reader"
    event_handler = CSVFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
