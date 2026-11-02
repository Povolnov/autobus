#!/usr/bin/env python3
"""Build trains.json with Alagón-Zaragoza trains from Renfe's open GTFS data (CC BY 4.0)."""
import csv, datetime as dt, io, json, re, sys, urllib.request, zipfile

URL = "https://ssl.renfe.com/gtransit/Fichero_AV_LD/google_transit.zip"
STATIONS = {"81210": "Alagón", "04040": "Delicias", "70806": "Portillo", "70807": "Goya", "71100": "Miraflores"}
ZARAGOZA = ["Delicias", "Portillo", "Goya", "Miraflores"]
MIN_TRAINS = 6  # refuse to publish a suspiciously small timetable


def table(z, name):
    text = z.read(name).decode("utf-8-sig")
    rows = csv.reader(io.StringIO(text))
    head = [h.strip() for h in next(rows)]
    for row in rows:
        if row:
            yield dict(zip(head, (c.strip() for c in row)))


def clock(value):
    h, m = value.split(":")[:2]
    return f"{int(h)}:{int(m):02d}"


def day(value):
    return dt.datetime.strptime(value, "%Y%m%d").date()


def build(z, today):
    stops = {}
    for r in table(z, "stop_times.txt"):
        if r["stop_id"] in STATIONS:
            stops.setdefault(r["trip_id"], []).append(r)
    services = {r["trip_id"]: r["service_id"] for r in table(z, "trips.txt") if r["trip_id"] in stops}
    wanted = set(services.values())
    calendar = {r["service_id"]: r for r in table(z, "calendar.txt") if r["service_id"] in wanted}
    removed, added = {}, {}
    for r in table(z, "calendar_dates.txt"):
        if r["service_id"] in wanted:
            (removed if r["exception_type"] == "2" else added).setdefault(r["service_id"], set()).add(day(r["date"]))

    names = "monday tuesday wednesday thursday friday saturday sunday".split()

    def runs(service, date):
        if date in added.get(service, ()):
            return True
        if date in removed.get(service, ()):
            return False
        c = calendar.get(service)
        return bool(c) and day(c["start_date"]) <= date <= day(c["end_date"]) and c[names[date.weekday()]] == "1"

    candidates = []
    last = today
    for trip, rows in stops.items():
        rows.sort(key=lambda r: int(r["stop_sequence"]))
        keys = [STATIONS[r["stop_id"]] for r in rows]
        if "Alagón" not in keys or not any(k in ZARAGOZA for k in keys):
            continue
        service = services.get(trip)
        c = calendar.get(service)
        if not c:
            continue
        last = max([last, day(c["end_date"]), *added.get(service, ())])
        match = re.match(r"^(\d+)\d(\d{4}-\d{2}-\d{2})$", trip)
        number = match.group(1) if match else re.sub(r"\D", "", trip)[:5]
        direction = "toZ" if keys[0] == "Alagón" else "toA"
        times = {STATIONS[r["stop_id"]]: clock(r["departure_time"]) for r in rows}
        candidates.append((number, direction, times, service))

    days = (last - today).days + 1
    merged = {}
    for number, direction, times, service in candidates:
        key = (number, direction, json.dumps(times, ensure_ascii=False))
        mask = merged.setdefault(key, ["0"] * days)
        for i in range(days):
            if runs(service, today + dt.timedelta(days=i)):
                mask[i] = "1"
    trains = [
        {"n": n, "d": d, "t": json.loads(t), "m": "".join(m)}
        for (n, d, t), m in sorted(merged.items()) if "1" in m
    ]
    return {"updated": today.isoformat(), "base": today.isoformat(), "days": days, "trains": trains}


def validate(data):
    trains = data["trains"]
    if len(trains) < MIN_TRAINS or {t["d"] for t in trains} != {"toZ", "toA"}:
        sys.exit(f"Refusing to publish: {len(trains)} trains found")
    if not any(t["m"][:7].count("1") for t in trains):
        sys.exit("Refusing to publish: no trains in the next 7 days")


def main():
    today = dt.datetime.now(dt.timezone.utc).date()
    request = urllib.request.Request(URL, headers={"User-Agent": "autobus-alagon/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        z = zipfile.ZipFile(io.BytesIO(response.read()))
    data = build(z, today)
    validate(data)
    with open("trains.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{len(data['trains'])} trains, {data['days']} days from {data['base']}")


if __name__ == "__main__":
    main()
