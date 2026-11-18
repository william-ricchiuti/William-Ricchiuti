#!/usr/bin/env python3
"""Draw the profile header for the current New Orleans weather.

1. Ask the National Weather Service (api.weather.gov, no key) for the hourly forecast.
2. Turn it into a scene: day/night, clear/partly/cloudy/rain/fog, real moon phase.
3. Write a Sierra-style narrator line (rotates each hour so it doesn't repeat all day).
4. Render the animated GIF.

  python update_header.py                     # live weather -> header.gif
  python update_header.py --mock period.json  # test with a saved forecast period
"""
import argparse, json, math, pathlib, re, sys, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import scene

LAT, LON = 29.9511, -90.0715                     # French Quarter
UA = "william-ricchiuti-profile-header (github.com/william-ricchiuti)"
TZ = ZoneInfo("America/Chicago")
STATUS = ("William Ricchiuti", "Making AI make sense")
MAX_LINE_PX = 112                                 # narrator box must clear the cathedral spires


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/geo+json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def current_period():
    pt = get(f"https://api.weather.gov/points/{LAT},{LON}")
    return get(pt["properties"]["forecastHourly"])["properties"]["periods"][0]


def moon_phase(when):
    """0 = new, .5 = full. Mean synodic month from the 2000-01-06 18:14 UTC new moon (good to ~a day)."""
    ref = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
    return ((when - ref).total_seconds() / 86400 / 29.530588853) % 1.0


def phase_name(p):
    names = ["new", "waxing crescent", "first quarter", "waxing gibbous",
             "full", "waning gibbous", "last quarter", "waning crescent"]
    return names[int((p * 8) + .5) % 8]


def heat_index(t, rh):
    if t < 80 or rh is None: return None
    return round(-42.379 + 2.04901523 * t + 10.14333127 * rh - .22475541 * t * rh - .00683783 * t * t
                 - .05481717 * rh * rh + .00122874 * t * t * rh + .00085282 * t * rh * rh - .00000199 * t * t * rh * rh)


def classify(period):
    f = (period.get("shortForecast") or "").lower()
    if re.search(r"rain|shower|drizzle|thunder|storm|sprinkle", f): sky = "rain"
    elif "fog" in f or "mist" in f: sky = "fog"
    elif "partly" in f: sky = "partly"
    elif re.search(r"cloudy|overcast", f) and "mostly clear" not in f and "mostly sunny" not in f: sky = "cloudy"
    else: sky = "clear"
    return sky, "thunder" in f


LINES = {
    "rain": [("It's {t}°F and raining", "in New Orleans."), ("Rain on the roofs.", "{t}°F in the Quarter."),
             ("{t}°F. The streets", "shine with rain.")],
    "thunder": [("Thunder and rain.", "{t}°F and pouring."), ("{t}°F. A storm rolls", "over the Quarter.")],
    "fog": [("Fog rolls in off the", "river. {t}°F."), ("{t}°F. The fog hides", "the skyline.")],
    "clear_night": [("A clear {t}°F night", "in the Quarter."), ("{t}°F. The moon is", "{phase}."),
                    ("Stars over Jackson", "Square. {t}°F.")],
    "new_moon": [("A clear {t}°F night.", "No moon tonight."), ("Stars over Jackson", "Square. {t}°F.")],
    "partly_night": [("{t}°F. Clouds drift", "past the moon."), ("A few clouds tonight.", "{t}°F.")],
    "cloudy_night": [("A cloudy {t}°F night", "in New Orleans."), ("No stars tonight.", "{t}°F and overcast.")],
    "clear_day": [("Sunny and {t}°F", "in New Orleans."), ("{t}°F and clear.", "Nice day for a ride."),
                  ("Blue skies over the", "Quarter. {t}°F.")],
    "hot": [("{t}°F, feels like {fl}°.", "Stay in the shade."), ("It's {t}°F. Even the", "pigeons are resting.")],
    "partly_day": [("{t}°F with a few", "clouds rolling by."), ("Partly sunny, {t}°F.", "Not bad at all.")],
    "cloudy_day": [("Gray skies and {t}°F", "over the Quarter."), ("Overcast and {t}°F", "in New Orleans.")],
    "cold": [("A chilly {t}°F.", "Grab a jacket, cher."), ("{t}°F in New Orleans.", "Gumbo weather.")],
}


def narrate(sky, thunder, tod, temp, feels, phase, hour):
    if sky == "rain": key = "thunder" if thunder else "rain"
    elif sky == "fog": key = "fog"
    elif temp <= 45: key = "cold"
    elif tod == "day" and feels and feels >= 95: key = "hot"
    elif tod == "night": key = {"clear": "new_moon" if phase_name(phase) == "new" else "clear_night",
                                 "partly": "partly_night", "cloudy": "cloudy_night"}[sky]
    else: key = {"clear": "clear_day", "partly": "partly_day", "cloudy": "cloudy_day"}[sky]
    opts = LINES[key]
    for k in range(len(opts)):                         # rotate by hour; skip any line too wide for the box
        a, b = opts[(hour + k) % len(opts)]
        lines = tuple(s.format(t=temp, fl=feels or temp, phase=phase_name(phase)) for s in (a, b))
        if all(scene.text_width(l) <= MAX_LINE_PX for l in lines): return lines
    return (f"It's {temp}°F", "in New Orleans.")


def build(period, now=None):
    now = now or datetime.now(TZ)
    temp = round(period["temperature"]) if period.get("temperatureUnit", "F") == "F" else round(period["temperature"] * 9 / 5 + 32)
    rh = (period.get("relativeHumidity") or {}).get("value")
    feels = heat_index(temp, rh)
    sky, thunder = classify(period)
    tod = "day" if period.get("isDaytime", 6 <= now.hour < 18) else "night"
    phase = moon_phase(now.astimezone(timezone.utc))
    cond = dict(tod=tod, sky=sky, moon=phase, hot=temp >= 88 and tod == "day")
    message = narrate(sky, thunder, tod, temp, feels, phase, now.hour)
    return cond, message


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock"); ap.add_argument("--out", default=str(pathlib.Path(__file__).parent / "header.gif"))
    a = ap.parse_args()
    try:
        period = json.loads(pathlib.Path(a.mock).read_text()) if a.mock else current_period()
    except Exception as e:                         # weather service hiccup: keep the last header
        print(f"weather fetch failed, leaving header unchanged: {e}", file=sys.stderr); return
    cond, message = build(period)
    scene.save_gif(scene.render(cond, STATUS, message), a.out)
    print(cond["tod"], cond["sky"], "|", " / ".join(message))


if __name__ == "__main__":
    main()
