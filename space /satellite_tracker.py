"""
============================================
  PAKISTANI SATELLITE TRACKER
  Tracks Pakistani satellites in real-time
  Uses: skyfield, matplotlib, requests
  Data: Celestrak (FREE, no API key needed)
============================================

INSTALL REQUIRED LIBRARIES:
    pip install skyfield matplotlib requests numpy

RUN:
    python pakistani_satellite_tracker.py
"""

import requests
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from datetime import datetime, timezone
from skyfield.api import load, EarthSatellite

# ─────────────────────────────────────────
#  PAKISTANI SATELLITES (CORRECTED NORAD IDs)
# ─────────────────────────────────────────
PAKISTANI_SATELLITES = {
    "PAKSAT-1R":  37747,   # Active Geostationary Communication Satellite
    "PAKSAT-MM1": 59911,   # Multi-Mission Satellite (Launched 2024)
    "PRSS-1":     43522,   # Pakistan Remote Sensing Satellite-1 (Replaced lunar ICUBE-Q)
    "PakTES-1A":  43422,   # Pakistan Technology Evaluation Satellite-1A
}

# Colors for each satellite on map
SAT_COLORS = {
    "PAKSAT-1R":  "#00FF88",
    "PAKSAT-MM1": "#FF6B35",
    "PRSS-1":     "#00BFFF",
    "PakTES-1A":  "#FFD700",
}

# ─────────────────────────────────────────
#  FETCH TLE DATA FROM CELESTRAK (MODERN API)
# ─────────────────────────────────────────
def fetch_tle_by_norad(norad_id):
    """Fetch TLE data for a satellite using its NORAD ID from modern CelesTrak GP API"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={norad_id}&FORMAT=tle"
    
    try:
        resp = requests.get(url, timeout=15, headers=headers)
        if resp.status_code == 200 and "1 " in resp.text:
            lines = [l.strip() for l in resp.text.strip().splitlines() if l.strip()]
            for i, line in enumerate(lines):
                if line.startswith("1 ") and i + 1 < len(lines) and lines[i+1].startswith("2 "):
                    return line, lines[i+1]
    except Exception:
        pass
    return None, None


def load_satellite_objects():
    """Load EarthSatellite objects for Pakistani satellites"""
    print("\n🛰️  Fetching Pakistani satellite TLE data from Celestrak...\n")
    
    ts = load.timescale()
    satellites = {}

    # Hardcoded robust fallback demo TLEs in case network issues happen during presentation
    demo_tles = {
        "PAKSAT-1R": (
            "1 37747U 11042A   26180.50000000  .00000000  00000-0  00000-0 0  9991",
            "2 37747   0.0200  75.5000 0003000   0.0000  38.0000  1.00270000  1234"
        ),
        "PAKSAT-MM1": (
            "1 59911U 24102A   26180.50000000  .00000000  00000-0  00000-0 0  9992",
            "2 59911   0.0100  38.2000 0002000   0.0000  45.0000  1.00270000   123"
        ),
        "PRSS-1": (
            "1 43522U 18056A   26180.50000000  .00001100  00000-0  45100-4 0  9995",
            "2 43522  98.0100 210.0000 0001200  85.0000 275.0000 14.82100000  152"
        ),
        "PakTES-1A": (
            "1 43422U 18042A   26180.50000000  .00001200  00000-0  58300-4 0  9998",
            "2 43422  97.7600 150.0000 0001500  90.0000 270.1000 14.95800000  280"
        ),
    }

    for sat_name, norad_id in PAKISTANI_SATELLITES.items():
        tle1, tle2 = fetch_tle_by_norad(norad_id)
        if tle1 and tle2:
            sat = EarthSatellite(tle1, tle2, sat_name, ts)
            satellites[sat_name] = sat
            print(f"  🟢 Live Data Loaded: {sat_name} (NORAD: {norad_id})")
        else:
            print(f"  ⚠️  Could not fetch live {sat_name}. Using built-in backup.")
            tle1, tle2 = demo_tles[sat_name]
            sat = EarthSatellite(tle1, tle2, sat_name, ts)
            satellites[sat_name] = sat

    return satellites, ts


# ─────────────────────────────────────────
#  GET CURRENT POSITION
# ─────────────────────────────────────────
def get_position(satellite, ts):
    """Returns (lat, lon, altitude_km) for a satellite right now"""
    t = ts.now()
    geocentric = satellite.at(t)
    subpoint = geocentric.subpoint()
    lat = subpoint.latitude.degrees
    lon = subpoint.longitude.degrees
    alt = subpoint.elevation.km
    return lat, lon, alt


def get_ground_track(satellite, ts, minutes=90):
    """Returns ground track for next `minutes` minutes"""
    now = ts.now()
    times = ts.utc(
        now.utc_datetime().replace(tzinfo=timezone.utc).year,
        now.utc_datetime().replace(tzinfo=timezone.utc).month,
        now.utc_datetime().replace(tzinfo=timezone.utc).day,
        now.utc_datetime().replace(tzinfo=timezone.utc).hour,
        now.utc_datetime().replace(tzinfo=timezone.utc).minute,
        range(0, minutes * 60, 120)   # every 2 minutes
    )
    geocentric = satellite.at(times)
    subpoints = geocentric.subpoint()
    lats = subpoints.latitude.degrees
    lons = subpoints.longitude.degrees
    return lats, lons


# ─────────────────────────────────────────
#  MAIN VISUALIZATION
# ─────────────────────────────────────────
def run_tracker(satellites, ts):
    print("\n🚀 Starting Live Pakistani Satellite Tracker...\n")

    fig = plt.figure(figsize=(16, 9), facecolor="#0A0E1A")
    fig.canvas.manager.set_window_title("🇵🇰 Pakistani Satellite Tracker — Live Dashboard")

    ax = fig.add_subplot(111)
    ax.set_facecolor("#0A0E1A")

    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_aspect('equal')

    # Grid lines
    for lon in range(-180, 181, 30):
        ax.axvline(lon, color="#1A2540", linewidth=0.4, zorder=0)
    for lat in range(-90, 91, 30):
        ax.axhline(lat, color="#1A2540", linewidth=0.4, zorder=0)

    # Load world map shapefile using GeoJSON data
    try:
        from matplotlib.patches import Polygon
        from matplotlib.collections import PatchCollection
        import urllib.request
        import json

        geo_url = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
        print("  🗺️  Loading world map...")
        
        req = urllib.request.Request(geo_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            geo_data = json.loads(response.read().decode())
        
        patches = []
        for feature in geo_data['features']:
            geom = feature['geometry']
            if geom['type'] == 'Polygon':
                coords = geom['coordinates'][0]
                poly = Polygon(coords, closed=True)
                patches.append(poly)
            elif geom['type'] == 'MultiPolygon':
                for part in geom['coordinates']:
                    coords = part[0]
                    poly = Polygon(coords, closed=True)
                    patches.append(poly)

        pc = PatchCollection(patches, facecolor="#1C2B45", edgecolor="#2A4070",
                             linewidth=0.3, zorder=1)
        ax.add_collection(pc)
        print("  ✅ World map loaded!")

    except Exception as e:
        print(f"  ⚠️  Could not load GeoJSON map ({e}). Falling back to simple bounds.")
        from matplotlib.patches import Rectangle
        rect = Rectangle((-180, -90), 360, 180,
                         linewidth=1, edgecolor="#2A4070",
                         facecolor="#1C2B45", zorder=1)
        ax.add_patch(rect)

    # Pakistan ground anchor point marker
    pak_lon, pak_lat = 69.3, 30.4  # Approximate center of Pakistan
    ax.plot(pak_lon, pak_lat, marker='*', color='#FFFFFF',
            markersize=12, zorder=10, label='Pakistan')
    ax.annotate('🇵🇰 Pakistan', (pak_lon, pak_lat),
                textcoords="offset points", xytext=(8, 5),
                fontsize=8, color='#FFFFFF', fontweight='bold', zorder=11)

    # Header
    ax.set_title(
        "🛰️  PAKISTANI SATELLITE TRACKER  —  LIVE",
        fontsize=16, color='#00FF88', fontweight='bold',
        fontfamily='monospace', pad=15
    )

    ax.set_xlabel("Longitude (°)", color='#7A8FB5', fontsize=9)
    ax.set_ylabel("Latitude (°)", color='#7A8FB5', fontsize=9)
    ax.tick_params(colors='#7A8FB5', labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor('#1A2540')

    # Instantiating layout objects
    sat_plots = {}
    info_texts = {}
    sat_names = list(satellites.keys())

    for i, name in enumerate(sat_names):
        color = SAT_COLORS.get(name, "#FFFFFF")
        dot, = ax.plot([], [], 'o', color=color, markersize=10, zorder=20, label=name)
        track, = ax.plot([], [], '-', color=color, alpha=0.3, linewidth=1, zorder=5)
        sat_plots[name] = (dot, track)
        
        # Dashboard telemetry side-panels
        info_texts[name] = ax.text(
            1.02, 0.95 - i * 0.23, "",
            transform=ax.transAxes,
            fontsize=8, color=color,
            fontfamily='monospace',
            verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5',
                      facecolor='#0A0E1A',
                      edgecolor=color,
                      alpha=0.85),
            zorder=25
        )

    # Universal Timestamp Counter
    time_text = ax.text(
        0.01, 0.02, "",
        transform=ax.transAxes,
        fontsize=9, color='#00FF88',
        fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='#0A0E1A',
                  edgecolor='#00FF88', alpha=0.8),
        zorder=25
    )

    ax.legend(loc='lower left', fontsize=8,
              facecolor='#0A0E1A', edgecolor='#2A4070',
              labelcolor='white', framealpha=0.9)

    # ── ANIMATION MATPLOTLIB RUNTIME ──────────────────
    def update(frame):
        now_utc = datetime.now(timezone.utc)
        time_text.set_text(f"⏱ UTC: {now_utc.strftime('%Y-%m-%d  %H:%M:%S')}")

        for name, sat in satellites.items():
            dot, track = sat_plots[name]

            try:
                lat, lon, alt = get_position(sat, ts)

                # Fetch and map out flight paths
                try:
                    track_lats, track_lons = get_ground_track(sat, ts, minutes=100)
                    track.set_data(track_lons, track_lats)
                except Exception:
                    pass

                dot.set_data([lon], [lat])

                # Geometric Horizon Coverage calculations
                visibility = "🟢 Link Available" if abs(lat - pak_lat) < 55 and abs(lon - pak_lon) < 55 else "🔴 Out of Range"
                info_texts[name].set_text(
                    f"━━ {name} ━━\n"
                    f"  LAT : {lat:+.2f}°\n"
                    f"  LON : {lon:+.2f}°\n"
                    f"  ALT : {alt:,.0f} km\n"
                    f"  {visibility}"
                )

            except Exception:
                info_texts[name].set_text(f"━━ {name} ━━\n  ⚠️ Telemetry Error")

        return [dot for dot, _ in sat_plots.values()] + \
               [track for _, track in sat_plots.values()] + \
               list(info_texts.values()) + [time_text]

    ani = animation.FuncAnimation(
        fig, update,
        interval=2000, # Tick update rate (2000ms)
        blit=False,
        cache_frame_data=False
    )

    # Use tight_layout with strict framing to stop side text panels clipping off-window
    plt.tight_layout(rect=[0, 0, 0.80, 1])

    print("  ✅ Tracker running! Close the canvas interface window to exit.\n")
    plt.show()


# ─────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("   🇵🇰  PAKISTANI SATELLITE TRACKER")
    print("   Real-time tracking | Celestrak API")
    print("=" * 50)

    try:
        satellites, ts = load_satellite_objects()

        if not satellites:
            print("\n❌ System failure. No tracking targets available.")
            exit(1)

        print(f"\n✅ Initialization completed: {len(satellites)} target spacecraft tracked.")
        run_tracker(satellites, ts)

    except KeyboardInterrupt:
        print("\n\n👋 Mission dashboard closed. Khuda Hafiz!")
    except ImportError as e:
        print(f"\n❌ Environment Dependency missing: {e}")
        print("\nPlease run install instruction:")
        print("    pip install skyfield matplotlib requests numpy")
