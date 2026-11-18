#!/usr/bin/env python3
"""Pick the right sketchbook scene for current New Orleans weather and write header.svg.

Data: National Weather Service (api.weather.gov) hourly forecast for New Orleans.
No API key needed; NWS only asks for a descriptive User-Agent.
Standard library only, so the GitHub Action needs no installs.

Usage:
  python update_header.py                    # live weather -> header.svg
  python update_header.py --mock mock.json   # test with a saved forecast period
"""
import argparse, json, pathlib, re, sys, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = pathlib.Path(__file__).parent
LAT, LON = 29.9511, -90.0715          # French Quarter
UA = "william-ricchiuti-profile-header (github.com/william-ricchiuti)"
TZ = ZoneInfo("America/Chicago")
CHIP_RIGHT, CHIP_PAD = 936, 34       # chip hugs the right edge, 17px padding per side
WET = re.compile(r"rain|shower|drizzle|thunder|storm|sprinkle", re.I)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/geo+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def current_period():
    pt = get(f"https://api.weather.gov/points/{LAT},{LON}")
    hourly = get(pt["properties"]["forecastHourly"])
    return hourly["properties"]["periods"][0]


def heat_index(t, rh):
    """NWS Rothfusz regression (°F). Only meaningful at 80°F and above."""
    if t < 80 or rh is None:
        return None
    hi = (-42.379 + 2.04901523 * t + 10.14333127 * rh - .22475541 * t * rh
          - .00683783 * t * t - .05481717 * rh * rh + .00122874 * t * t * rh
          + .00085282 * t * rh * rh - .00000199 * t * t * rh * rh)
    return round(hi)


def build(period, now=None):
    now = now or datetime.now(TZ)
    temp = round(period["temperature"]) if period.get("temperatureUnit", "F") == "F" \
        else round(period["temperature"] * 9 / 5 + 32)
    sky = (period.get("shortForecast") or "").strip()
    rh = (period.get("relativeHumidity") or {}).get("value")

    if WET.search(sky):
        scene = "rain"
    else:
        scene = "day" if period.get("isDaytime", 6 <= now.hour < 18) else "night"
        s = sky.lower()
        if "partly" in s:                                   # partly cloudy / partly sunny
            scene += "-partly"
        elif re.search(r"cloudy|overcast|fog", s) and "mostly clear" not in s and "mostly sunny" not in s:
            scene += "-cloudy"

    words = sky.lower().replace("chance ", "").replace("slight ", "").replace("likely", "").strip() or "clear"
    if "thunder" in words:
        words = "thunderstorms"
    elif "shower" in words:
        words = "showers"
    hi = heat_index(temp, rh)
    parts = [f"{temp}°F", f"feels like {hi}°" if hi and hi >= temp + 3 else words]
    parts.append(now.strftime("%-I %p").replace("AM", "AM CT").replace("PM", "PM CT"))
    caption = " · ".join(parts)

    widths = json.loads((HERE / "char_widths.json").read_text())
    text_w = sum(widths.get(c, 7.8) for c in caption)
    chip_w = round(text_w + CHIP_PAD)
    svg = (HERE / "templates" / f"{scene}.svg").read_text()
    svg = (svg.replace("{{CAPTION}}", caption)
              .replace("{{CHIP_W}}", str(chip_w))
              .replace("{{CHIP_X}}", str(CHIP_RIGHT - chip_w))
              .replace("{{CAP_X}}", str(round(CHIP_RIGHT - chip_w / 2, 1)))
              .replace("{{HEAT}}", "inline" if temp >= 85 else "none"))
    return scene, caption, svg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", help="JSON file holding one NWS forecast period")
    ap.add_argument("--out", default=str(HERE / "header.svg"))
    a = ap.parse_args()
    try:
        period = json.loads(pathlib.Path(a.mock).read_text()) if a.mock else current_period()
    except Exception as e:  # NWS hiccup: keep yesterday's header rather than fail loudly
        print(f"weather fetch failed, leaving header unchanged: {e}", file=sys.stderr)
        return
    scene, caption, svg = build(period)
    pathlib.Path(a.out).write_text(svg)
    print(f"{scene}: {caption}")


if __name__ == "__main__":
    main()
