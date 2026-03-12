# ─────────────────────────────────────────────────────────────────────────────
# Google Sheets Configuration
# ─────────────────────────────────────────────────────────────────────────────
SHEET_ID = "1VQ5imSEh-L8zRClN8PBijPpuu-oGVm-LF8ioPRcsO1I"

# Tab name → GID mapping. Find GID in the URL: ...#gid=XXXXXX
SHEET_TABS = {
    "Gesamtliste beide sortiert Touren": 1652287,
}

DEFAULT_TAB = "Gesamtliste beide sortiert Touren"

# ─────────────────────────────────────────────────────────────────────────────
# Geocoding
# ─────────────────────────────────────────────────────────────────────────────
GEOCODE_CACHE_FILE = "geocode_cache.json"
NOMINATIM_USER_AGENT = "fenner-route-visualizer/1.0"
NOMINATIM_DELAY = 1.1  # seconds between Nominatim requests (rate limit: 1/sec)

# ─────────────────────────────────────────────────────────────────────────────
# Map
# ─────────────────────────────────────────────────────────────────────────────
MAP_CENTER_LAT = 53.55   # Hamburg
MAP_CENTER_LON = 10.00
MAP_ZOOM = 10

# ─────────────────────────────────────────────────────────────────────────────
# Column names (as they appear in the sheet)
# ─────────────────────────────────────────────────────────────────────────────
COL_STREET       = "Straße"             # street incl. house number
COL_PLZ          = "PLZ"
COL_CITY         = "Ort"
COL_NAME         = "Name Einsender"
COL_TIME         = "Abholzeit Basis"    # e.g. "09:00 Uhr"
COL_TIME_RANGE   = "Abholzeitspanne"    # e.g. "08:50 - 09:00"
COL_ADDRESS_INFO = "Info"
COL_TOUR_ID      = "Tour"
COL_FIRMA        = "Firma"
COL_LAB_DAYS     = "Labortage"

# Day columns in the sheet (leer = wird bedient, X = wird NICHT bedient)
DAY_COLUMNS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

DAY_LABELS = {
    "Mo": "Montag",
    "Di": "Dienstag",
    "Mi": "Mittwoch",
    "Do": "Donnerstag",
    "Fr": "Freitag",
    "Sa": "Samstag",
    "So": "Sonntag",
}

# ─────────────────────────────────────────────────────────────────────────────
# Tour colors – 20 visually distinct hex colors
# ─────────────────────────────────────────────────────────────────────────────
TOUR_COLOR_PALETTE = [
    "#e41a1c",  # red
    "#377eb8",  # blue
    "#4daf4a",  # green
    "#984ea3",  # purple
    "#ff7f00",  # orange
    "#a65628",  # brown
    "#f781bf",  # pink
    "#17becf",  # cyan
    "#8c564b",  # dark brown
    "#e377c2",  # magenta
    "#7f7f7f",  # grey
    "#bcbd22",  # olive
    "#1b9e77",  # teal
    "#d95f02",  # burnt orange
    "#7570b3",  # indigo
    "#e7298a",  # hot pink
    "#66a61e",  # lime
    "#e6ab02",  # gold
    "#a6761d",  # tan
    "#666666",  # dark grey
]
