import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from pathlib import Path

import config
import geocoder

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fenner Route Visualizer",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# Basic Auth
# ─────────────────────────────────────────────────────────────────────────────

_AUTH_USER = "logistik"
_AUTH_PASS = "limbach"


def check_auth() -> bool:
    """Show login form if not authenticated. Returns True if authenticated."""
    if st.session_state.get("authenticated"):
        return True

    st.markdown("## 🔐 Anmeldung")
    with st.form("login_form"):
        username = st.text_input("Benutzername")
        password = st.text_input("Passwort", type="password")
        submitted = st.form_submit_button("Anmelden", use_container_width=True)
        if submitted:
            if username == _AUTH_USER and password == _AUTH_PASS:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Ungültige Anmeldedaten.")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner="Lade Google Sheet…")
def load_sheet(sheet_id: str, gid: int) -> pd.DataFrame:
    url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/export?format=csv&gid={gid}"
    )
    try:
        # Row 0 is the legend ("X = KEINE Abholung"), Row 1 is the actual header
        df = pd.read_csv(url, dtype=str, header=1)
        df = df.fillna("")
        # Normalize column names (they may contain \n from multi-line headers)
        df.columns = [c.replace("\n", " ").strip() for c in df.columns]
        # Strip leading/trailing whitespace from all string columns
        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].str.strip()
        return df
    except Exception as e:
        st.error(f"Fehler beim Laden des Sheets: {e}")
        st.info(
            "Stelle sicher, dass das Sheet auf "
            "**'Jeder mit dem Link kann es ansehen'** gesetzt ist."
        )
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def is_active_on_day(row, day_col: str) -> bool:
    """leer = wird bedient, X (oder beliebiger Text) = wird NICHT bedient."""
    val = str(row.get(day_col, "")).strip()
    return val == ""  # empty = active


@st.cache_data
def assign_tour_colors(tour_ids: tuple) -> dict:
    palette = config.TOUR_COLOR_PALETTE
    return {
        tour_id: palette[i % len(palette)]
        for i, tour_id in enumerate(sorted(tour_ids))
    }


def format_active_days(row) -> str:
    active = [
        config.DAY_LABELS[d]
        for d in config.DAY_COLUMNS
        if is_active_on_day(row, d)
    ]
    return ", ".join(active) if active else "–"


def make_popup_html(row) -> str:
    name = row.get(config.COL_NAME, "") or "–"
    tour = row.get(config.COL_TOUR_ID, "") or "–"
    zeit = row.get(config.COL_TIME, "") or "–"
    firma = row.get(config.COL_FIRMA, "") or "–"
    lab_days = row.get(config.COL_LAB_DAYS, "") or "–"
    addr_info = row.get(config.COL_ADDRESS_INFO, "") or ""
    on_demand = row.get(config.COL_ON_DEMAND, "") or ""
    abc = row.get(config.COL_ABC, "") or ""

    street = row.get(config.COL_STREET, "") or ""
    plz = row.get(config.COL_PLZ, "") or ""
    city = row.get(config.COL_CITY, "") or ""
    address = f"{street}, {plz} {city}".strip(", ")

    active_days_str = format_active_days(row)

    rows_data = [
        ("Tour", tour),
        ("Abholzeit", zeit),
        ("Firma", firma),
        ("Labortage 2025", lab_days),
        ("Aktive Tage", active_days_str),
        ("Adresse", address),
    ]
    if on_demand:
        rows_data.append(("Bei Bedarf", on_demand))
    if addr_info:
        rows_data.append(("Adress-Info", addr_info))
    if abc:
        rows_data.append(("ABC", abc))

    table_rows = "".join(
        f'<tr>'
        f'<td style="padding:3px 10px 3px 0;color:#555;white-space:nowrap;vertical-align:top">'
        f'<b>{label}</b></td>'
        f'<td style="padding:3px 0;vertical-align:top">{value}</td>'
        f'</tr>'
        for label, value in rows_data
    )

    return f"""
    <div style="font-family:sans-serif;font-size:13px;min-width:260px;max-width:370px">
      <div style="font-weight:bold;font-size:15px;margin-bottom:8px;
                  color:#1a1a2e;border-bottom:2px solid #eee;padding-bottom:6px">
        {name}
      </div>
      <table style="border-collapse:collapse;width:100%">
        {table_rows}
      </table>
    </div>
    """


# ─────────────────────────────────────────────────────────────────────────────
# Map builder
# ─────────────────────────────────────────────────────────────────────────────

def _parse_zeit_minutes(zeit_str: str) -> float:
    """Parse '07:30 Uhr' → minutes since midnight for sorting. Returns inf if unparseable."""
    val = str(zeit_str).replace(" Uhr", "").strip()
    try:
        h, m = val.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return float("inf")


def build_map(
    df: pd.DataFrame,
    tour_colors: dict,
    show_lines: bool,
) -> folium.Map:
    df_geo = df.dropna(subset=["lat", "lon"]).copy()
    df_geo["lat"] = df_geo["lat"].astype(float)
    df_geo["lon"] = df_geo["lon"].astype(float)

    if df_geo.empty:
        center = [config.MAP_CENTER_LAT, config.MAP_CENTER_LON]
        zoom = config.MAP_ZOOM
    else:
        center = [df_geo["lat"].mean(), df_geo["lon"].mean()]
        lat_range = df_geo["lat"].max() - df_geo["lat"].min()
        zoom = 12 if lat_range < 0.5 else (10 if lat_range < 2 else 8)

    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="CartoDB positron",
    )

    # Route lines (per tour, sorted by Abholzeit)
    if show_lines:
        for tour_id, group in df_geo.groupby(config.COL_TOUR_ID, sort=False):
            color = tour_colors.get(tour_id, "#888888")
            # Sort stops by Zeit (HH:MM Uhr) so lines follow the real route order
            group = group.copy()
            group["_sort_min"] = group[config.COL_TIME].apply(_parse_zeit_minutes)
            group = group.sort_values("_sort_min")
            coords = list(zip(group["lat"], group["lon"]))
            if len(coords) > 1:
                folium.PolyLine(
                    coords,
                    color=color,
                    weight=3,
                    opacity=0.65,
                    tooltip=f"Tour: {tour_id}",
                ).add_to(m)

    # Stop markers
    for _, row in df_geo.iterrows():
        tour_id = row.get(config.COL_TOUR_ID, "")
        color = tour_colors.get(tour_id, "#888888")
        name = row.get(config.COL_NAME, "?") or "?"
        zeit = row.get(config.COL_TIME, "") or ""

        tooltip_html = (
            f"<b>{name}</b><br>"
            f"<span style='color:#666'>Tour: {tour_id}</span>"
            + (f" &nbsp;|&nbsp; {zeit}" if zeit else "")
        )

        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=8,
            color="white",
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.9,
            tooltip=folium.Tooltip(tooltip_html, sticky=False),
            popup=folium.Popup(make_popup_html(row), max_width=400),
        ).add_to(m)

    return m


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

def render_sidebar(all_tours: list) -> tuple:
    """Render sidebar and return (sheet_id, gid, selected_days, selected_tours, show_lines)."""
    st.sidebar.title("⚙️ Einstellungen")

    # ── Sheet config ──────────────────────────────────────────────────────────
    with st.sidebar.expander("📊 Google Sheet", expanded=False):
        sheet_id = st.text_input(
            "Sheet ID",
            value=config.SHEET_ID,
            help="Die ID aus der Google-Sheet-URL",
        )
        tab_names = list(config.SHEET_TABS.keys())
        selected_tab = st.selectbox("Tab", options=tab_names, index=0)
        gid = st.number_input(
            "Tab GID",
            value=int(config.SHEET_TABS[selected_tab]),
            step=1,
            format="%d",
            help="GID aus der URL: ...#gid=XXXXXX",
        )
        if st.button("🔄 Sheet neu laden", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    # ── Day filter ────────────────────────────────────────────────────────────
    with st.sidebar.expander("📅 Tage", expanded=True):
        selected_days = []
        for day in config.DAY_COLUMNS:
            if st.checkbox(config.DAY_LABELS[day], value=True, key=f"day_{day}"):
                selected_days.append(day)

    # ── Tour filter ───────────────────────────────────────────────────────────
    with st.sidebar.expander("🚗 Touren", expanded=True):
        tour_mode = st.radio(
            "tour_mode",
            ["Alle Touren", "Auswahl"],
            horizontal=True,
            label_visibility="collapsed",
        )
        if tour_mode == "Auswahl":
            selected_tours = st.multiselect(
                "Touren auswählen",
                options=all_tours,
                default=all_tours[:1] if all_tours else [],
                label_visibility="collapsed",
            )
        else:
            selected_tours = all_tours

    # ── Options ───────────────────────────────────────────────────────────────
    with st.sidebar.expander("🔧 Optionen", expanded=False):
        show_lines = st.checkbox("Routen-Linien anzeigen", value=True)

    # ── Geocoding ─────────────────────────────────────────────────────────────
    with st.sidebar.expander("📍 Geocoding", expanded=False):
        cache_file = Path(config.GEOCODE_CACHE_FILE)
        if cache_file.exists():
            try:
                import json
                cache = json.loads(cache_file.read_text(encoding="utf-8"))
                n_total = len(cache)
                n_ok = sum(1 for v in cache.values() if v is not None)
                n_fail = n_total - n_ok
                st.caption(f"Cache: **{n_ok}** Adressen, {n_fail} fehlgeschlagen")
            except Exception:
                st.caption("Cache vorhanden")
        else:
            st.caption("Kein Cache vorhanden – wird beim Start erstellt.")

        if st.button("🗑️ Cache leeren & neu geocoden", use_container_width=True):
            cache_file.unlink(missing_ok=True)
            st.success("Cache geleert.")
            st.rerun()

    # ── Logout ────────────────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Abmelden", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

    return sheet_id, int(gid), selected_days, selected_tours, show_lines


# ─────────────────────────────────────────────────────────────────────────────
# Main app
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Auth gate
    if not check_auth():
        return

    st.title("🗺️ Fenner Route Visualizer")

    # ── Load data (sheet_id/gid needed before sidebar filters) ────────────────
    # We need a preliminary sidebar render for sheet config only.
    # Use session state to persist sheet_id and gid across reruns.
    if "sheet_id" not in st.session_state:
        st.session_state["sheet_id"] = config.SHEET_ID
    if "gid" not in st.session_state:
        st.session_state["gid"] = int(list(config.SHEET_TABS.values())[0])

    df_raw = load_sheet(st.session_state["sheet_id"], st.session_state["gid"])
    if df_raw.empty:
        st.warning("Keine Daten geladen.")
        # Still render minimal sidebar so sheet config is accessible
        render_sidebar([])
        return

    # Remove rows with no Tour-ID (empty header rows etc.)
    df_raw = df_raw[df_raw[config.COL_TOUR_ID].str.strip() != ""].copy()

    df, cache = geocoder.geocode_dataframe(df_raw)

    # ── Tour metadata ─────────────────────────────────────────────────────────
    all_tours = sorted(df[config.COL_TOUR_ID].unique().tolist())
    tour_colors = assign_tour_colors(tuple(all_tours))

    # ── Full sidebar (with filters) ───────────────────────────────────────────
    sheet_id, gid, selected_days, selected_tours, show_lines = render_sidebar(all_tours)

    # Persist sheet config in session state so it survives reruns
    st.session_state["sheet_id"] = sheet_id
    st.session_state["gid"] = gid

    # ── Guard: no tour selected ───────────────────────────────────────────────
    if not selected_tours:
        st.info("👈 Bitte mindestens eine Tour in der Seitenleiste auswählen.")
        return

    # ── Filter dataframe ──────────────────────────────────────────────────────
    df_filtered = df[df[config.COL_TOUR_ID].isin(selected_tours)].copy()

    if selected_days:
        mask = df_filtered.apply(
            lambda row: any(is_active_on_day(row, d) for d in selected_days),
            axis=1,
        )
        df_filtered = df_filtered[mask]

    # ── Status caption ────────────────────────────────────────────────────────
    n_total = len(df_filtered)
    n_geo = df_filtered.dropna(subset=["lat", "lon"]).shape[0]
    n_missing = n_total - n_geo

    status_parts = [f"**{n_total}** Stops"]
    if n_missing > 0:
        status_parts.append(f"⚠️ {n_missing} ohne Koordinaten")
    st.caption("  ·  ".join(status_parts))

    # ── Map ───────────────────────────────────────────────────────────────────
    m = build_map(df_filtered, tour_colors, show_lines)
    st_folium(
        m,
        use_container_width=True,
        height=800,
        returned_objects=[],
        key=f"map_{','.join(selected_tours)}_{','.join(selected_days)}_{show_lines}",
    )

    # ── Legend ────────────────────────────────────────────────────────────────
    if selected_tours:
        st.markdown("---")
        st.markdown("**Legende**")
        # Show in rows of 6
        chunk_size = 6
        for i in range(0, len(selected_tours), chunk_size):
            chunk = selected_tours[i : i + chunk_size]
            cols = st.columns(chunk_size)
            for j, tour_id in enumerate(chunk):
                color = tour_colors.get(tour_id, "#888")
                cols[j].markdown(
                    f'<span style="display:inline-block;width:14px;height:14px;'
                    f'background:{color};border-radius:50%;vertical-align:middle;'
                    f'margin-right:5px"></span>'
                    f'<span style="font-size:13px">{tour_id}</span>',
                    unsafe_allow_html=True,
                )

    # ── Data table ────────────────────────────────────────────────────────────
    with st.expander("📋 Datentabelle anzeigen", expanded=False):
        display_cols = [
            c
            for c in [
                config.COL_TOUR_ID,
                config.COL_NAME,
                config.COL_TIME,
                config.COL_FIRMA,
                config.COL_STREET,
                config.COL_CITY,
                *config.DAY_COLUMNS,
                config.COL_LAB_DAYS,
                config.COL_ADDRESS_INFO,
            ]
            if c in df_filtered.columns
        ]
        # Sort table by Tour-ID, then by Zeit (chronological)
        df_table = df_filtered[display_cols].copy()
        df_table["_sort_min"] = df_filtered[config.COL_TIME].apply(_parse_zeit_minutes)
        df_table = df_table.sort_values(
            [config.COL_TOUR_ID, "_sort_min"]
        ).drop(columns=["_sort_min"]).reset_index(drop=True)
        st.dataframe(df_table, use_container_width=True, height=400)


if __name__ == "__main__":
    main()
