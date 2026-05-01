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
from matplotlib.patches import FancyArrowPatch
from datetime import datetime, timezone
from skyfield.api import load, EarthSatellite

# ─────────────────────────────────────────
#  PAKISTANI SATELLITES (NORAD IDs)
# ─────────────────────────────────────────
PAKISTANI_SATELLITES = {
    "PAKSAT-1R":  21869,   # Main communication satellite
    "PAKSAT-MM1": 40890,   # Multi-mission satellite
    "ICUBE-Q":    57166,   # Pakistan's lunar cubesat (iCube Qamar)
    "PakTES-1A":  43422,   # Pakistan remote sensing satellite
}

# Colors for each satellite on map
SAT_COLORS = {
    "PAKSAT-1R":  "#00FF88",
    "PAKSAT-MM1": "#FF6B35",
    "ICUBE-Q":    "#00BFFF",
    "PakTES-1A":  "#FFD700",
}

# ─────────────────────────────────────────
#  FETCH TLE DATA FROM CELESTRAK (FREE)
# ─────────────────────────────────────────
def fetch_tle_by_norad(norad_id, name):
    """Fetch TLE data for a satellite using its NORAD ID from Celestrak"""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    urls = [
        f"https://celestrak.org/SOCRATES/query.php?ID={norad_id}&TYPE=SAT&FORMAT=TLE",
        f"https://celestrak.org/satcat/tle.php?CATNR={norad_id}",
        f"https://celestrak.org/cgi-bin/tle.pl?CATNR={norad_id}",
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=25, headers=headers)
            if resp.status_code == 200:
                lines = [l.strip() for l in resp.text.strip().splitlines() if l.strip()]
                for i, line in enumerate(lines):
                    if line.startswith("1 ") and i + 1 < len(lines) and lines[i+1].startswith("2 "):
                        return line, lines[i+1]
        except Exception:
            continue
    return None, None


def fetch_all_active_tle():
    """Fetch all active satellites TLE from Celestrak"""
    url = "https://celestrak.org/SOCRATES/query.php?catalog=active&FORMAT=TLE"
    fallback_url = "https://celestrak.org/pub/TLE/catalog.txt"
    try:
        resp = requests.get("https://celestrak.org/SOCRATES/query.php?catalog=active&FORMAT=TLE", timeout=15)
        return resp.text
    except Exception:
        try:
            resp = requests.get(fallback_url, timeout=15)
            return resp.text
        except Exception:
            return ""


def load_satellite_objects():
    """Load EarthSatellite objects for Pakistani satellites"""
    print("\n🛰️  Fetching Pakistani satellite TLE data from Celestrak...\n")
    
    ts = load.timescale()
    satellites = {}

    # Try fetching from Celestrak's GEOSTATIONARY and ACTIVE catalog
    catalog_urls = [
        "https://celestrak.org/SOCRATES/query.php?catalog=geo&FORMAT=TLE",
        "https://celestrak.org/SOCRATES/query.php?catalog=active&FORMAT=TLE",
        "https://celestrak.org/pub/TLE/geo.txt",
        "https://celestrak.org/pub/TLE/active.txt",
    ]

    all_tle_text = ""
    for url in catalog_urls:
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200 and len(resp.text) > 100:
                all_tle_text += resp.text
                print(f"  ✅ Fetched catalog: {url.split('/')[-1]}")
        except Exception as e:
            print(f"  ⚠️  Could not fetch {url.split('/')[-1]}: {e}")

    # Parse TLE text into dict: {norad_id: (name, tle1, tle2)}
    tle_catalog = {}
    lines = [l.strip() for l in all_tle_text.splitlines() if l.strip()]
    i = 0
    while i < len(lines) - 2:
        if lines[i+1].startswith("1 ") and lines[i+2].startswith("2 "):
            sat_name = lines[i]
            tle1 = lines[i+1]
            tle2 = lines[i+2]
            try:
                norad = int(tle1[2:7].strip())
                tle_catalog[norad] = (sat_name, tle1, tle2)
            except ValueError:
                pass
            i += 3
        else:
            i += 1

    # Match Pakistani satellites
    for sat_name, norad_id in PAKISTANI_SATELLITES.items():
        if norad_id in tle_catalog:
            _, tle1, tle2 = tle_catalog[norad_id]
            sat = EarthSatellite(tle1, tle2, sat_name, ts)
            satellites[sat_name] = sat
            print(f"  🟢 Loaded: {sat_name} (NORAD: {norad_id})")
        else:
            # Try direct fetch
            tle1, tle2 = fetch_tle_by_norad(norad_id, sat_name)
            if tle1 and tle2:
                sat = EarthSatellite(tle1, tle2, sat_name, ts)
                satellites[sat_name] = sat
                print(f"  🟢 Loaded (direct): {sat_name} (NORAD: {norad_id})")
            else:
                print(f"  🔴 Could not load: {sat_name} (NORAD: {norad_id})")

    # Always fill missing satellites with demo TLE data
    demo_tles = {
        "PAKSAT-1R": (
            "1 21869U 92009A   24001.50000000  .00000000  00000-0  00000-0 0  9991",
            "2 21869   0.0500  68.3000 0003000   0.0000 110.0000  1.00270000 11674"
        ),
        "PakTES-1A": (
            "1 43422U 18042A   24001.50000000  .00001200  00000-0  58300-4 0  9998",
            "2 43422  97.7600 150.0000 0001500  90.0000 270.1000 14.95800000 28000"
        ),
        "PAKSAT-MM1": (
            "1 40890U 15049A   24001.50000000  .00000000  00000-0  00000-0 0  9993",
            "2 40890   0.0300  38.5000 0002500   0.0000  75.0000  1.00270000  8760"
        ),
        "ICUBE-Q": (
            "1 57166U 22143B   24001.50000000  .00000500  00000-0  12400-4 0  9996",
            "2 57166  98.4300 200.0000 0008000  45.0000 315.2000 14.57000000 15230"
        ),
    }

    if not satellites:
        print("\n  Warning: No satellites loaded from API. Using demo TLE data...\n")

    for name, (tle1, tle2) in demo_tles.items():
        if name not in satellites:
            try:
                sat = EarthSatellite(tle1, tle2, name, ts)
                satellites[name] = sat
                print(f"  Demo loaded: {name}")
            except Exception as e:
                print(f"  Failed for {name}: {e}")

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

    # Load world map image from matplotlib basemap-style using just matplotlib
    fig = plt.figure(figsize=(16, 9), facecolor="#0A0E1A")
    fig.canvas.manager.set_window_title("🇵🇰 Pakistani Satellite Tracker — Live")

    ax = fig.add_subplot(111)
    ax.set_facecolor("#0A0E1A")

    # Draw world map using a simple coordinate grid
    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_aspect('equal')

    # Grid lines
    for lon in range(-180, 181, 30):
        ax.axvline(lon, color="#1A2540", linewidth=0.4, zorder=0)
    for lat in range(-90, 91, 30):
        ax.axhline(lat, color="#1A2540", linewidth=0.4, zorder=0)

    # Load world map shapefile using matplotlib's built-in data
    try:
        from matplotlib.patches import Polygon
        from matplotlib.collections import PatchCollection
        import urllib.request
        import json

        # Use a simple GeoJSON world map
        geo_url = "https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
        print("  🗺️  Loading world map...")
        
        with urllib.request.urlopen(geo_url) as response:
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
        print(f"  ⚠️  Could not load GeoJSON map ({e}). Using outline only.")
        # Draw a simple rectangular world outline
        from matplotlib.patches import Rectangle
        rect = Rectangle((-180, -90), 360, 180,
                         linewidth=1, edgecolor="#2A4070",
                         facecolor="#1C2B45", zorder=1)
        ax.add_patch(rect)

    # Pakistan highlight
    pak_lon, pak_lat = 69.3, 30.4  # Approximate center of Pakistan
    ax.plot(pak_lon, pak_lat, marker='*', color='#FFFFFF',
            markersize=12, zorder=10, label='Pakistan')
    ax.annotate('🇵🇰 Pakistan', (pak_lon, pak_lat),
                textcoords="offset points", xytext=(8, 5),
                fontsize=8, color='#FFFFFF', fontweight='bold', zorder=11)

    # Title
    title_text = ax.set_title(
        "🛰️  PAKISTANI SATELLITE TRACKER  —  LIVE",
        fontsize=16, color='#00FF88', fontweight='bold',
        fontfamily='monospace', pad=15
    )

    ax.set_xlabel("Longitude (°)", color='#7A8FB5', fontsize=9)
    ax.set_ylabel("Latitude (°)", color='#7A8FB5', fontsize=9)
    ax.tick_params(colors='#7A8FB5', labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor('#1A2540')

    # Satellite plot objects (dot + label + ground track)
    sat_plots = {}
    info_texts = {}

    sat_names = list(satellites.keys())

    for i, name in enumerate(sat_names):
        color = SAT_COLORS.get(name, "#FFFFFF")
        dot, = ax.plot([], [], 'o', color=color, markersize=10,
                       zorder=20, label=name)
        track, = ax.plot([], [], '-', color=color, alpha=0.3,
                         linewidth=1, zorder=5)
        sat_plots[name] = (dot, track)
        # Info text on right side
        info_texts[name] = ax.text(
            1.01, 0.95 - i * 0.22, "",
            transform=ax.transAxes,
            fontsize=8, color=color,
            fontfamily='monospace',
            verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.4',
                      facecolor='#0A0E1A',
                      edgecolor=color,
                      alpha=0.8),
            zorder=25
        )

    # Time display
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

    # ── ANIMATION UPDATE ──────────────────
    def update(frame):
        now_utc = datetime.now(timezone.utc)
        time_text.set_text(f"⏱ UTC: {now_utc.strftime('%Y-%m-%d  %H:%M:%S')}")

        for name, sat in satellites.items():
            color = SAT_COLORS.get(name, "#FFFFFF")
            dot, track = sat_plots[name]

            try:
                lat, lon, alt = get_position(sat, ts)

                # Ground track
                try:
                    track_lats, track_lons = get_ground_track(sat, ts, minutes=60)
                    # Handle longitude wrapping for plot
                    track.set_data(track_lons, track_lats)
                except Exception:
                    pass

                # Current position dot
                dot.set_data([lon], [lat])

                # Info box
                visibility = "🟢 Visible from PK" if abs(lat - pak_lat) < 45 and abs(lon - pak_lon) < 60 else "🔴 Not visible"
                info_texts[name].set_text(
                    f"━━ {name} ━━\n"
                    f"  LAT : {lat:+.2f}°\n"
                    f"  LON : {lon:+.2f}°\n"
                    f"  ALT : {alt:,.0f} km\n"
                    f"  {visibility}"
                )

            except Exception as e:
                info_texts[name].set_text(f"━━ {name} ━━\n  ⚠️  Error")

        return [dot for dot, _ in sat_plots.values()] + \
               [track for _, track in sat_plots.values()] + \
               list(info_texts.values()) + [time_text]

    ani = animation.FuncAnimation(
        fig, update,
        interval=2000,     # update every 2 seconds
        blit=False,
        cache_frame_data=False
    )

    plt.tight_layout(rect=[0, 0, 0.82, 1])
    plt.subplots_adjust(right=0.80)

    print("  ✅ Tracker running! Close the window to exit.\n")
    print("  📡 Satellites being tracked:")
    for name in satellites:
        print(f"     • {name}")
    print()

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
            print("\n❌ No satellites could be loaded. Check internet connection.")
            exit(1)

        print(f"\n✅ {len(satellites)} satellite(s) loaded successfully!")
        run_tracker(satellites, ts)

    except KeyboardInterrupt:
        print("\n\n👋 Tracker stopped. Khuda Hafiz!")
    except ImportError as e:
        print(f"\n❌ Missing library: {e}")
        print("\nPlease install required libraries:")
        print("    pip install skyfield matplotlib requests numpy")
