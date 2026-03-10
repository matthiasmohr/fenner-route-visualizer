# 🗺️ Fenner Route Visualizer

Interaktive Karte zur Visualisierung der Labor-Abholrouten von Dr. Fenner & Kollegen. Daten kommen live aus einem Google Sheet.

---

## Features

- **Interaktive Karte** – farbkodierte Routen mit klickbaren Stops
- **Stop-Details per Klick** – Name, Abholzeit, Firma, Labortage, aktive Tage, Adresse
- **Tages-Filter** – Mo bis So; leer = Stop wird bedient, X = nicht bedient
- **Touren-Filter** – alle Touren oder gezielt einzelne anzeigen
- **Routen-Linien** – verbinden Stops in chronologischer Reihenfolge (nach Abholzeit)
- **Live Google Sheet** – Daten werden automatisch alle 5 Minuten neu geladen
- **Geocoding-Cache** – Adressen werden einmalig via Nominatim geocodiert und in `geocode_cache.json` gecacht; neue Adressen werden automatisch ergänzt

---

## Schnellstart

```bash
# Abhängigkeiten installieren
.venv/bin/python -m pip install -r requirements.txt

# App starten
.venv/bin/streamlit run app.py
```

Öffnet sich automatisch unter **http://localhost:8501**

---

## Projektstruktur

```
fenner-route-visualizer/
├── app.py                  # Haupt-App (Streamlit UI + Karten-Logik)
├── config.py               # Konfiguration (Sheet ID, Spalten, Farben)
├── geocoder.py             # Geocoding: JSON-Cache + Nominatim-Fallback
├── geocode_cache.json      # 502 Adressen gecacht (im Git committed)
├── requirements.txt        # Python-Abhängigkeiten
└── .claude/launch.json     # Claude Preview Konfiguration
```

---

## Google Sheet konfigurieren

Das Sheet muss auf **„Jeder mit dem Link kann es ansehen"** gesetzt sein.

Standard-Konfiguration in `config.py`:

| Parameter | Wert |
|---|---|
| `SHEET_ID` | `1VQ5imSEh-L8zRClN8PBijPpuu-oGVm-LF8ioPRcsO1I` |
| `DEFAULT_TAB` | `Gesamtliste beide sortiert Touren` |
| Tab-GID | `1898711273` |

Sheet-ID und Tab lassen sich auch direkt in der App-Sidebar ändern.

### Sheet-Format

| Spalte | Inhalt |
|---|---|
| `Straße Hs.-Nr.` | Straße + Hausnummer |
| `PLZ` | Postleitzahl (Format: `D-XXXXX`) |
| `Ort` | Stadt |
| `Name` | Einsender-Name |
| `Mo` – `So` | leer = wird bedient, `X` = wird **nicht** bedient |
| `Zeit` | Abholzeit (Format: `07:30 Uhr`) |
| `Tour-ID` | Routenkennung (z. B. `Rot`, `HNO-Nord`) |
| `Firma` | Kurierdienst |
| `Labortage 2025` | Anzahl Labortage |
| `Adress-Info1` | Sonderhinweise zur Adresse |

---

## Geocoding

Beim ersten Start werden alle Adressen via [Nominatim (OpenStreetMap)](https://nominatim.openstreetmap.org/) geocodiert. Das dauert bei ~500 Adressen ca. **10 Minuten** (Rate-Limit: 1 Anfrage/Sekunde).

Die Ergebnisse werden in `geocode_cache.json` gespeichert – diese Datei ist im Git, damit alle Teammitglieder sofort davon profitieren.

**Cache leeren:** Sidebar → Geocoding → „Cache leeren & neu geocoden"

> **Hinweis:** 36 Adressen konnten nicht geocodiert werden, da sie Sonderangaben enthalten (z. B. „Depot: …", Stockwerkangaben). Diese Stops erscheinen nicht auf der Karte, sind aber in der Datentabelle sichtbar.

---

## Abhängigkeiten

| Paket | Zweck |
|---|---|
| `streamlit` | Web-UI |
| `pandas` | Datenverarbeitung |
| `folium` | Interaktive Karten |
| `streamlit-folium` | Folium in Streamlit einbetten |
| `requests` | Nominatim-API-Anfragen |
