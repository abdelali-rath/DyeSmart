# main.py - Haarfarben App mit Datenbankintegration
import kivy
kivy.require('2.0.0')

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.uix.image import Image as KivyImage
import threading
import os

# Für Dateiauswahl
from tkinter import Tk, filedialog
import tkinter as tk

# Datenbank importieren
import sqlite3
from typing import List, Tuple

# Bildanalyse importieren
try:
    from image_analysis import analyze_hair_image_simple
    HAS_IMAGE_ANALYSIS = True
except ImportError:
    HAS_IMAGE_ANALYSIS = False
    print("Hinweis: image_analysis.py nicht gefunden, Demo-Modus aktiv")

Window.size = (500, 700)

# Datenbank-Konfiguration
DB_FILENAME = "haircolor_practice.db"

class HairColorDatabase:
    """Datenbank-Manager für Haarfarben-Rezepte"""
    
    def __init__(self):
        self.db_path = DB_FILENAME
        self.init_database()
    
    def ensure_db_folder(self, path: str):
        folder = os.path.dirname(path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder, exist_ok=True)
    
    def compute_recipe_text(self, s_depth:int, s_nu:float, t_depth:int, t_nu:float) -> Tuple[str, str]:
        """
        Realistische, praxisnahe Rezept-Logik
        """
        level_diff = t_depth - s_depth
        recipe_steps = []
        oxidant = "10 Vol"

        # Determine oxidant for up to 4 levels after possible bleach
        remain_lift = min(level_diff, 4) if level_diff > 0 else 0

        if remain_lift <= 0:
            oxidant = "10 Vol"
        elif remain_lift <= 1:
            oxidant = "10 Vol"
        elif remain_lift <= 2:
            oxidant = "20 Vol"
        elif remain_lift <= 3:
            oxidant = "30 Vol"
        else:
            oxidant = "40 Vol"

        # If large lift required -> need bleach
        if level_diff > 4:
            bleach_lift = level_diff - 4
            intermediate_depth = s_depth + bleach_lift
            if intermediate_depth >= t_depth:
                intermediate_depth = max(t_depth - 1, s_depth + 1)
            recipe_steps.append(f"1) Blondierung: Aufhellen von {s_depth} → {intermediate_depth} (Blondierung, kontrolliert, bis zu {bleach_lift} Stufen)")
            recipe_steps.append(f"2) Tonung/Farbe: Farbauftrag zur Feinanpassung auf {t_depth}.{int(t_nu*10)} mit Oxidant {oxidant}")
        else:
            if level_diff > 0:
                recipe_steps.append(f"1) Farbauftrag: von {s_depth} → {t_depth} mit Oxidant {oxidant}")
            elif level_diff == 0:
                recipe_steps.append(f"1) Nuancierung / Refresh: Farbe {t_depth}.{int(t_nu*10)} (keine Aufhellung)")
            else:
                recipe_steps.append(f"1) Dunkeln: von {s_depth} → {t_depth} (Farbtiefe verringern) mit Oxidant {oxidant}")

        # Nuance correction
        def nuance_correction_text(src_n, tgt_n):
            if tgt_n == src_n:
                return None
            counter = {
                0.0: "Neutralisierung (nur Toner)",
                0.1: "Aschbeimischung zur Neutralisation warmer Töne",
                0.3: "Gold/warme Nuance (leicht glänzend)",
                0.4: "Kupferzugabe für warme Reflexe",
                0.6: "Rotanteile (für lebendige rote Reflexe)",
                0.7: "Violett (gegen Gelbstich)",
                0.8: "Blau/Pearl (gegen orange/rote Störpigmente)"
            }
            return counter.get(tgt_n, None)

        corr = nuance_correction_text(s_nu, t_nu)
        if corr:
            recipe_steps.append(f"Nuance-Korrektur: {corr}")

        recipe_steps.append(f"Mischverhältnis: Farbtube + Entwicklungsflüssigkeit gemäß Hersteller; evtl. 1:1.5 für Toner.")
        recipe_text = "\n".join(recipe_steps)
        return recipe_text, oxidant
    
    def init_database(self, db_path: str = None):
        """Initialisiert die Datenbank"""
        if db_path:
            self.db_path = db_path
        
        self.ensure_db_folder(self.db_path)
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # create tables
        c.executescript("""
        CREATE TABLE IF NOT EXISTS Product_Line (
            product_id INTEGER PRIMARY KEY,
            brand TEXT,
            code TEXT,
            type TEXT,
            oxidant_vol INTEGER,
            note TEXT
        );
        CREATE TABLE IF NOT EXISTS Color_Base (
            base_id INTEGER PRIMARY KEY,
            name TEXT,
            lab_l_center REAL,
            lab_a_center REAL,
            lab_b_center REAL,
            depth INTEGER,
            nuance REAL
        );
        CREATE TABLE IF NOT EXISTS Recipe_Combination (
            combo_id INTEGER PRIMARY KEY,
            source_depth INTEGER,
            target_depth INTEGER,
            source_nuance REAL,
            target_nuance REAL,
            recipe_formula TEXT,
            oxidant_code TEXT
        );
        """)

        # insert product lines (oxidants)
        products = [
            (1, "ProColor", "10 Vol", "Oxidant", 3, "Nur Nuancierung / dunkeln"),
            (2, "ProColor", "20 Vol", "Oxidant", 6, "Leichte Aufhellung"),
            (3, "ProColor", "30 Vol", "Oxidant", 9, "Normale Aufhellung"),
            (4, "ProColor", "40 Vol", "Oxidant", 12, "Starke Aufhellung"),
            (5, "ProMix", "Toner", "Toner", None, "Toner zur Nuancierung"),
        ]
        c.executemany("INSERT OR IGNORE INTO Product_Line VALUES (?, ?, ?, ?, ?, ?)", products)

        # base colors
        base_colors = [
            (101, "Tief 3.0 Neutral", 25.0, 0.0, 0.0, 3, 0.0),
            (102, "Mittel 5.3 Gold", 40.0, 5.0, 15.0, 5, 0.3),
            (103, "Hell 7.4 Kupfer", 60.0, 10.0, 20.0, 7, 0.4),
            (104, "Hell 8.7 Violett", 65.0, 20.0, -10.0, 8, 0.7),
        ]
        c.executemany("INSERT OR IGNORE INTO Color_Base VALUES (?, ?, ?, ?, ?, ?, ?)", base_colors)

        # populate Recipe_Combination
        c.execute("SELECT COUNT(*) FROM Recipe_Combination")
        if c.fetchone()[0] == 0:
            combos = []
            DEPTH_VALUES = list(range(1, 11))
            NUANCE_VALUES = [0.0, 0.1, 0.3, 0.4, 0.6, 0.7, 0.8]
            total = len(DEPTH_VALUES)*len(DEPTH_VALUES)*len(NUANCE_VALUES)*len(NUANCE_VALUES)
            print(f"Erzeuge ca. {total} Rezeptkombinationen...")
            for s in DEPTH_VALUES:
                for t in DEPTH_VALUES:
                    for sn in NUANCE_VALUES:
                        for tn in NUANCE_VALUES:
                            recipe_text, ox = self.compute_recipe_text(s, sn, t, tn)
                            combos.append((s, t, sn, tn, recipe_text, ox))
            c.executemany("""
                INSERT INTO Recipe_Combination (source_depth, target_depth, source_nuance, target_nuance, recipe_formula, oxidant_code)
                VALUES (?, ?, ?, ?, ?, ?)
            """, combos)
            print("Datenbank: Rezeptkombinationen eingefügt.")

        conn.commit()
        conn.close()
        print(f"Datenbank initialisiert: {self.db_path}")
        return True
    
    def get_recipe_from_db(self, source_depth: int, source_nuance: float, 
                          target_depth: int, target_nuance: float) -> Tuple[str, str]:
        """
        Holt das Rezept aus der Datenbank
        """
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute("""
                SELECT recipe_formula, oxidant_code 
                FROM Recipe_Combination 
                WHERE source_depth = ? AND target_depth = ?
                AND source_nuance = ? AND target_nuance = ?
            """, (source_depth, target_depth, source_nuance, target_nuance))
            
            result = c.fetchone()
            conn.close()
            
            if result:
                return result[0], result[1]
            else:
                # Fallback: Berechne Rezept
                return self.compute_recipe_text(source_depth, source_nuance, target_depth, target_nuance)
                
        except Exception as e:
            print(f"Datenbankfehler: {e}")
            # Fallback
            return self.compute_recipe_text(source_depth, source_nuance, target_depth, target_nuance)

class HairApp(App):
    def build(self):
        # Datenbank initialisieren
        self.database = HairColorDatabase()
        threading.Thread(target=self.init_database_background, daemon=True).start()
        
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Titel
        title = Label(text='HAARFARBEN ANALYSE', font_size=26, size_hint_y=None, height=60)
        self.layout.add_widget(title)
        
        # Statusleiste
        self.status = Label(text='Bereit', size_hint_y=None, height=30, color=(0.6, 0.6, 0.6, 1))
        self.layout.add_widget(self.status)
        
        # Modus-Auswahl
        mode_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        self.manual_btn = Button(text='Manuell', background_color=(0.2, 0.6, 0.8, 1))
        self.image_btn = Button(text='Bild', background_color=(0.2, 0.8, 0.6, 1))
        self.manual_btn.bind(on_press=self.show_manual)
        self.image_btn.bind(on_press=self.show_image_upload)
        mode_layout.add_widget(self.manual_btn)
        mode_layout.add_widget(self.image_btn)
        self.layout.add_widget(mode_layout)
        
        # Haupt-Inhaltsbereich
        self.content_area = BoxLayout(orientation='vertical', size_hint_y=1)
        self.layout.add_widget(self.content_area)
        
        # Standard: Manuelle Eingabe
        self.show_manual(None)
        
        return self.layout
    
    def init_database_background(self):
        """Initialisiert die Datenbank im Hintergrund"""
        try:
            self.database.init_database()
            Clock.schedule_once(lambda dt: self.update_status("Datenbank geladen", (0, 0.7, 0, 1)), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.update_status(f"Datenbankfehler: {e}", (1, 0, 0, 1)), 0)
    
    def clear_content(self):
        self.content_area.clear_widgets()
    
    def update_status(self, text, color=(0.6, 0.6, 0.6, 1)):
        self.status.text = text
        self.status.color = color
    
    def show_manual(self, instance):
        self.clear_content()
        self.update_status("Manuelle Eingabe")
        
        # Aktuelle Farbe
        self.content_area.add_widget(Label(text='Aktuelle Haarfarbe:', font_size=18, size_hint_y=None, height=40))
        
        grid1 = GridLayout(cols=2, size_hint_y=None, height=80, spacing=10)
        grid1.add_widget(Label(text='Tiefe (1-10):'))
        self.current_depth = TextInput(text='5', multiline=False, input_filter='int')
        grid1.add_widget(self.current_depth)
        
        grid1.add_widget(Label(text='Nuance:'))
        self.current_nuance = TextInput(text='0.3', multiline=False)
        grid1.add_widget(self.current_nuance)
        self.content_area.add_widget(grid1)
        
        # Gewünschte Farbe
        self.content_area.add_widget(Label(text='Gewünschte Haarfarbe:', font_size=18, size_hint_y=None, height=40))
        
        grid2 = GridLayout(cols=2, size_hint_y=None, height=80, spacing=10)
        grid2.add_widget(Label(text='Tiefe (1-10):'))
        self.target_depth = TextInput(text='7', multiline=False, input_filter='int')
        grid2.add_widget(self.target_depth)
        
        grid2.add_widget(Label(text='Nuance:'))
        self.target_nuance = TextInput(text='0.1', multiline=False)
        grid2.add_widget(self.target_nuance)
        self.content_area.add_widget(grid2)
        
        # Nuance Hilfe
        help_text = "Nuancen: 0.0=Neutral, 0.1=Asch, 0.3=Gold, 0.4=Kupfer, 0.6=Rot, 0.7=Violett, 0.8=Blau"
        help_label = Label(text=help_text, size_hint_y=None, height=40, font_size=12, color=(0.5, 0.5, 0.5, 1))
        self.content_area.add_widget(help_label)
        
        # Berechnen Button
        calc_btn = Button(text='REZEPT BERECHNEN', size_hint_y=None, height=60, 
                         background_color=(0.8, 0.2, 0.4, 1), font_size=18)
        calc_btn.bind(on_press=self.calculate_recipe_from_db)
        self.content_area.add_widget(calc_btn)
        
        # Ergebnisbereich
        self.result_label = Label(text='', size_hint_y=1, halign='left', valign='top')
        scroll = ScrollView(size_hint_y=1)
        scroll.add_widget(self.result_label)
        self.content_area.add_widget(scroll)
    
    def show_image_upload(self, instance):
        self.clear_content()
        self.update_status("Bild hochladen")
        
        self.content_area.add_widget(Label(text='Bildanalyse:', font_size=18, size_hint_y=None, height=40))
        
        # Große Bild-Button
        self.image_button = Button(text='BILD AUSWÄHLEN\n(Klicken zum Öffnen)', 
                                  size_hint_y=None, height=120,
                                  background_color=(0.4, 0.6, 0.9, 1),
                                  font_size=20)
        self.image_button.bind(on_press=self.select_image_file)
        self.content_area.add_widget(self.image_button)
        
        # Datei-Info
        self.file_info = Label(text='Kein Bild ausgewählt', 
                              size_hint_y=None, height=40,
                              color=(0.5, 0.5, 0.5, 1))
        self.content_area.add_widget(self.file_info)
        
        # Mini-Vorschau (platzhalter)
        self.preview_label = Label(text='Vorschau erscheint hier', 
                                  size_hint_y=None, height=100)
        self.content_area.add_widget(self.preview_label)
        
        # Ziel-Eingabe
        self.content_area.add_widget(Label(text='Ziel-Haarfarbe:', font_size=18, size_hint_y=None, height=40))
        
        grid = GridLayout(cols=2, size_hint_y=None, height=80, spacing=10)
        grid.add_widget(Label(text='Tiefe (1-10):'))
        self.image_target_depth = TextInput(text='7', multiline=False, input_filter='int')
        grid.add_widget(self.image_target_depth)
        
        grid.add_widget(Label(text='Nuance:'))
        self.image_target_nuance = TextInput(text='0.1', multiline=False)
        grid.add_widget(self.image_target_nuance)
        self.content_area.add_widget(grid)
        
        # Analyse Button
        analyze_btn = Button(text='ANALYSIEREN', size_hint_y=None, height=60,
                           background_color=(0.4, 0.2, 0.8, 1))
        analyze_btn.bind(on_press=self.start_image_analysis)
        self.content_area.add_widget(analyze_btn)
        
        # Ergebnis
        self.image_result = Label(text='', size_hint_y=1, halign='left', valign='top')
        scroll = ScrollView(size_hint_y=1)
        scroll.add_widget(self.image_result)
        self.content_area.add_widget(scroll)
    
    def select_image_file(self, instance):
        """Einfache Dateiauswahl mit tkinter"""
        try:
            # tkinter Fenster verstecken
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            # Datei öffnen Dialog
            file_path = filedialog.askopenfilename(
                title="Bild auswählen",
                filetypes=[
                    ("Bilder", "*.png *.jpg *.jpeg *.bmp"),
                    ("Alle Dateien", "*.*")
                ],
                initialdir=os.path.expanduser("~")
            )
            
            if file_path:
                self.selected_image_path = file_path
                filename = os.path.basename(file_path)
                self.file_info.text = f"Ausgewählt: {filename}"
                self.image_button.text = f'{filename[:20]}...\n(Klicken zum Ändern)'
                self.image_button.background_color = (0.2, 0.8, 0.4, 1)
                self.update_status(f"Bild geladen: {filename}")
                
                # Mini-Vorschau-Text
                try:
                    import cv2
                    img = cv2.imread(file_path)
                    if img is not None:
                        h, w = img.shape[:2]
                        self.preview_label.text = f"Bild: {w}x{h} Pixel"
                    else:
                        self.preview_label.text = "Bild geladen"
                except:
                    self.preview_label.text = "Bild geladen"
            
            root.destroy()
            
        except Exception as e:
            print(f"Fehler bei Dateiauswahl: {e}")
            # Fallback: Einfacher Popup
            self.show_simple_file_dialog()
    
    def show_simple_file_dialog(self):
        """Einfacher Datei-Dialog als Fallback"""
        content = BoxLayout(orientation='vertical', padding=10)
        
        # Nur Bilder-Ordner anzeigen
        pics_dir = os.path.join(os.path.expanduser('~'), 'Pictures')
        if not os.path.exists(pics_dir):
            pics_dir = os.path.expanduser('~')
        
        # Einfache Auswahl von bekannten Orten
        content.add_widget(Label(text="Bitte wählen Sie einen Ordner:", size_hint_y=None, height=40))
        
        buttons_box = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None, height=200)
        
        # Desktop
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        if os.path.exists(desktop):
            btn = Button(text=f'Desktop ({len(os.listdir(desktop))} Dateien)',
                        size_hint_y=None, height=50)
            btn.bind(on_press=lambda x: self.browse_folder(desktop))
            buttons_box.add_widget(btn)
        
        # Bilder
        if os.path.exists(pics_dir):
            btn = Button(text=f'Bilder-Ordner',
                        size_hint_y=None, height=50)
            btn.bind(on_press=lambda x: self.browse_folder(pics_dir))
            buttons_box.add_widget(btn)
        
        # Downloads
        downloads = os.path.join(os.path.expanduser('~'), 'Downloads')
        if os.path.exists(downloads):
            btn = Button(text=f'Downloads',
                        size_hint_y=None, height=50)
            btn.bind(on_press=lambda x: self.browse_folder(downloads))
            buttons_box.add_widget(btn)
        
        content.add_widget(buttons_box)
        
        # Manueller Pfad
        manual_box = BoxLayout(size_hint_y=None, height=50, spacing=5)
        self.manual_path = TextInput(text=pics_dir, multiline=False, size_hint_x=0.7)
        manual_btn = Button(text='Öffnen', size_hint_x=0.3)
        manual_btn.bind(on_press=lambda x: self.browse_folder(self.manual_path.text))
        manual_box.add_widget(self.manual_path)
        manual_box.add_widget(manual_btn)
        content.add_widget(manual_box)
        
        popup = Popup(title='Ordner auswählen', content=content, size_hint=(0.8, 0.6))
        
        cancel_btn = Button(text='Abbrechen', size_hint_y=None, height=40)
        cancel_btn.bind(on_press=popup.dismiss)
        content.add_widget(cancel_btn)
        
        popup.open()
    
    def browse_folder(self, folder_path):
        """Zeigt Bilder in einem Ordner"""
        if not os.path.exists(folder_path):
            self.update_status("Ordner existiert nicht", (1, 0, 0, 1))
            return
        
        # Bilder im Ordner finden
        image_files = []
        for f in os.listdir(folder_path):
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                image_files.append(os.path.join(folder_path, f))
        
        if not image_files:
            self.update_status(f"Keine Bilder in {os.path.basename(folder_path)}", (1, 0, 0, 1))
            return
        
        # Popup mit Bildauswahl
        content = BoxLayout(orientation='vertical', padding=10)
        content.add_widget(Label(text=f"Bilder in {os.path.basename(folder_path)}:", 
                               size_hint_y=None, height=40))
        
        scroll = ScrollView(size_hint_y=1)
        grid = GridLayout(cols=1, spacing=5, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))
        
        for img_path in image_files[:20]:  # Max 20 Bilder
            filename = os.path.basename(img_path)
            btn = Button(text=f"{filename}", 
                        size_hint_y=None, height=50,
                        background_color=(0.7, 0.8, 0.9, 1))
            btn.bind(on_press=lambda x, path=img_path: self.select_specific_image(path))
            grid.add_widget(btn)
        
        scroll.add_widget(grid)
        content.add_widget(scroll)
        
        popup = Popup(title='Bild auswählen', content=content, size_hint=(0.9, 0.8))
        
        cancel_btn = Button(text='Zurück', size_hint_y=None, height=40)
        cancel_btn.bind(on_press=popup.dismiss)
        content.add_widget(cancel_btn)
        
        popup.open()
    
    def select_specific_image(self, image_path):
        """Spezifisches Bild auswählen"""
        self.selected_image_path = image_path
        filename = os.path.basename(image_path)
        self.file_info.text = f"Ausgewählt: {filename}"
        self.image_button.text = f'{filename[:20]}...\n(Klicken zum Ändern)'
        self.image_button.background_color = (0.2, 0.8, 0.4, 1)
        self.update_status(f"Bild geladen: {filename}")
        
        # Alle Popups schließen
        App.get_running_app().root_window.children[0].dismiss()
    
    def start_image_analysis(self, instance):
        if not hasattr(self, 'selected_image_path'):
            self.image_result.text = "Bitte erst ein Bild auswählen"
            return
        
        file_path = self.selected_image_path
        
        if not os.path.exists(file_path):
            self.image_result.text = "Bilddatei existiert nicht mehr"
            return
        
        # Dateityp prüfen
        valid_ext = ['.png', '.jpg', '.jpeg', '.bmp']
        if not any(file_path.lower().endswith(ext) for ext in valid_ext):
            self.image_result.text = 'Nur Bilddateien (png, jpg, jpeg, bmp)'
            return
        
        self.image_result.text = "Analysiere Bild...\nBitte warten..."
        
        # In separatem Thread analysieren
        def analyze_thread():
            try:
                if HAS_IMAGE_ANALYSIS:
                    result = analyze_hair_image_simple(file_path)
                else:
                    # Demo-Fallback
                    result = {
                        "source_depth": 5,
                        "source_nuance": 0.3,
                        "info": "Demo-Modus (keine echte Analyse)",
                        "avg_color": [120, 100, 80]
                    }
                
                # Zurück zum UI-Thread
                Clock.schedule_once(lambda dt: self.show_analysis_result_with_db(result), 0)
                
            except Exception as e:
                Clock.schedule_once(lambda dt: self.show_analysis_error(str(e)), 0)
        
        threading.Thread(target=analyze_thread, daemon=True).start()
    
    def show_analysis_result_with_db(self, result):
        if "error" in result:
            self.image_result.text = f'FEHLER:\n{result["error"]}'
            return
        
        # Zielwerte holen
        try:
            target_depth = int(self.image_target_depth.text)
            target_nuance = float(self.image_target_nuance.text)
        except:
            target_depth = 7
            target_nuance = 0.1
        
        source_depth = result.get("source_depth", 5)
        source_nuance = result.get("source_nuance", 0.3)
        
        # Rezept aus Datenbank holen (im Hintergrund)
        def get_recipe_thread():
            try:
                recipe_text, oxidant = self.database.get_recipe_from_db(
                    source_depth, source_nuance, 
                    target_depth, target_nuance
                )
                
                # Ergebnis anzeigen
                info = result.get("info", "Bild analysiert")
                avg_color = result.get("avg_color", [0, 0, 0])
                
                result_text = f"""BILDANALYSE ERFOLGREICH

{info}

ERKANNT:
• Haartiefe: Stufe {source_depth}
• Nuance: {source_nuance}
• Durchschnittsfarbe: RGB{avg_color}

REZEPT AUS DATENBANK:
Oxidant: {oxidant}

{recipe_text}"""
                
                Clock.schedule_once(lambda dt: setattr(self.image_result, 'text', result_text), 0)
                
            except Exception as e:
                error_text = f"FEHLER BEIM REZEPT ABRUF:\n{str(e)}"
                Clock.schedule_once(lambda dt: setattr(self.image_result, 'text', error_text), 0)
        
        threading.Thread(target=get_recipe_thread, daemon=True).start()
    
    def show_analysis_error(self, error):
        self.image_result.text = f"ANALYSE FEHLGESCHLAGEN:\n{error}"
    
    def calculate_recipe_from_db(self, instance):
        """Berechnet Rezept aus Datenbank"""
        try:
            current_depth = int(self.current_depth.text)
            current_nuance = float(self.current_nuance.text)
            target_depth = int(self.target_depth.text)
            target_nuance = float(self.target_nuance.text)
            
            # Validierung
            if not (1 <= current_depth <= 10) or not (1 <= target_depth <= 10):
                self.result_label.text = "Tiefe muss zwischen 1-10 sein"
                return
            
            valid_nuances = [0.0, 0.1, 0.3, 0.4, 0.6, 0.7, 0.8]
            if current_nuance not in valid_nuances or target_nuance not in valid_nuances:
                self.result_label.text = f"Nuance muss sein: {valid_nuances}"
                return
            
            # Ladeanzeige
            self.result_label.text = "Rezept wird aus Datenbank geladen..."
            
            # Rezept aus Datenbank holen (im Hintergrund)
            def get_recipe_thread():
                try:
                    recipe_text, oxidant = self.database.get_recipe_from_db(
                        current_depth, current_nuance, 
                        target_depth, target_nuance
                    )
                    
                    result_text = f"""REZEPT GEFUNDEN

AUSGANGSLAGE:
• Aktuell: Stufe {current_depth}.{int(current_nuance*10)} ({self.get_nuance_name(current_nuance)})
• Ziel: Stufe {target_depth}.{int(target_nuance*10)} ({self.get_nuance_name(target_nuance)})

REZEPT AUS DATENBANK:
Oxidant: {oxidant}

{recipe_text}"""
                    
                    Clock.schedule_once(lambda dt: setattr(self.result_label, 'text', result_text), 0)
                    
                except Exception as e:
                    error_text = f"FEHLER BEIM REZEPT ABRUF:\n{str(e)}"
                    Clock.schedule_once(lambda dt: setattr(self.result_label, 'text', error_text), 0)
            
            threading.Thread(target=get_recipe_thread, daemon=True).start()
            
        except ValueError:
            self.result_label.text = "Bitte gültige Zahlen eingeben"
        except Exception as e:
            self.result_label.text = f"Fehler: {str(e)}"
    
    def get_nuance_name(self, nuance):
        names = {
            0.0: "Neutral",
            0.1: "Asch",
            0.3: "Gold",
            0.4: "Kupfer",
            0.6: "Rot",
            0.7: "Violett",
            0.8: "Blau"
        }
        return names.get(nuance, "Unbekannt")

if __name__ == '__main__':
    HairApp().run()