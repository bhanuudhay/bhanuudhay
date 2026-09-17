"""Render a WakaTime "activity last year" heatmap to SVG. Stdlib only."""
import base64
import datetime as dt
import json
import os
import urllib.request

API = "https://wakatime.com/api/v1/users/current/insights/days/last_year"
OUT = os.environ.get("HEATMAP_OUT", "assets/wakatime-heatmap.svg")

CELL, GAP, RADIUS = 11, 2, 2
PAD_L, PAD_T = 34, 38
LEVELS = ["#1b2027", "#28486c", "#3a6698", "#5b89bd", "#9dbde0", "#e9f1fb"]
BG, FG, MUTED = "#0d1117", "#c9d1d9", "#8b949e"


def fetch(key):
    auth = base64.b64encode(key.encode()).decode()
    req = urllib.request.Request(API, headers={"Authorization": f"Basic {auth}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["data"]["days"]


def bucket(seconds, thresholds):
    if seconds <= 0:
        return 0
    for i, t in enumerate(thresholds, start=1):
        if seconds <= t:
            return i
    return len(thresholds) + 1


def build(days):
    by_date = {d["date"]: d.get("total", 0.0) for d in days}
    nonzero = sorted(v for v in by_date.values() if v > 0)
    if nonzero:
        q = [nonzero[int(len(nonzero) * f)] for f in (0.2, 0.4, 0.6, 0.8)]
    else:
        q = [1, 2, 3, 4]

    start = dt.date.fromisoformat(min(by_date)) if by_date else dt.date.today()
    end = dt.date.fromisoformat(max(by_date)) if by_date else dt.date.today()
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday

    cells, months, col = [], [], 0
    day, last_month = start, None
    while day <= end:
        row = (day.weekday() + 1) % 7
        if row == 0 and day > start:
            col += 1
        if day.month != last_month:
            if not months or col - months[-1][0] >= 3:
                months.append((col, day.strftime("%b")))
            last_month = day.month
        secs = by_date.get(day.isoformat(), 0.0)
        cells.append((col, row, bucket(secs, q), day, secs))
        day += dt.timedelta(days=1)

    weeks = col + 1
    w = PAD_L + weeks * (CELL + GAP) + 20
    h = PAD_T + 7 * (CELL + GAP) + 26
    total_h = sum(by_date.values()) / 3600

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<rect width="{w}" height="{h}" rx="6" fill="{BG}"/>',
        f'<text x="{PAD_L}" y="18" fill="{FG}" font-size="12" font-weight="600" '
        f'letter-spacing="0.6">ACTIVITY LAST YEAR</text>',
        f'<text x="{w - 20}" y="18" fill="{MUTED}" font-size="11" text-anchor="end">'
        f'{total_h:,.0f} hrs</text>',
    ]
    for c, name in months:
        p.append(
            f'<text x="{PAD_L + c * (CELL + GAP)}" y="{PAD_T - 8}" fill="{MUTED}" '
            f'font-size="10">{name}</text>'
        )
    for row, name in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = PAD_T + row * (CELL + GAP) + CELL - 1
        p.append(f'<text x="4" y="{y}" fill="{MUTED}" font-size="9">{name}</text>')
    for c, row, lvl, day, secs in cells:
        x, y = PAD_L + c * (CELL + GAP), PAD_T + row * (CELL + GAP)
        hrs = secs / 3600
        label = "no activity" if secs <= 0 else f"{hrs:.1f} hrs"
        p.append(
            f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="{RADIUS}" '
            f'fill="{LEVELS[lvl]}"><title>{day.isoformat()}: {label}</title></rect>'
        )
    lx, ly = w - 20 - (len(LEVELS) * (CELL + GAP)) - 62, h - 17
    p.append(f'<text x="{lx}" y="{ly + 9}" fill="{MUTED}" font-size="10">Less</text>')
    for i, col_ in enumerate(LEVELS):
        p.append(
            f'<rect x="{lx + 28 + i * (CELL + GAP)}" y="{ly}" width="{CELL}" '
            f'height="{CELL}" rx="{RADIUS}" fill="{col_}"/>'
        )
    p.append(
        f'<text x="{lx + 34 + len(LEVELS) * (CELL + GAP)}" y="{ly + 9}" '
        f'fill="{MUTED}" font-size="10">More</text>'
    )
    p.append("</svg>")
    return "\n".join(p)


def main():
    key = os.environ.get("WAKATIME_API_KEY", "").strip()
    if not key:
        raise SystemExit("WAKATIME_API_KEY is not set")
    svg = build(fetch(key))
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
