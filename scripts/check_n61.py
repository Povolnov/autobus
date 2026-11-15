"""Weekly check of the night bus N61 timetable (static in the apps).

There is no open data feed for N61, so we watch a public page that publishes it.
If its times or its stop-map image change, open a GitHub issue so the timetable
can be updated by hand. Network failures never raise an alarm.
"""
import hashlib, json, os, re, subprocess, sys, urllib.request

PAGE = "https://soydezaragoza.es/buho-n61-de-zaragoza-a-utebo-casetas-pinseque-y-alagon-horarios-y-paradas/"
EXPECT = ["3:30", "4:05", "4:20"]          # times the apps use (Zaragoza out, Alagón in, Alagón out)
STATE = "scripts/n61_state.json"

def get(url, method="GET"):
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "Mozilla/5.0 (n61-watch)"})
    return urllib.request.urlopen(req, timeout=30)

try:
    html = get(PAGE).read().decode("utf-8", "replace")
except Exception as e:
    print("page not reachable, skipping:", e); sys.exit(0)

text = re.sub(r"<[^>]+>", " ", html)
missing = [t for t in EXPECT if t not in text]
img = re.search(r"https?://[^\"'\s]*paradas-buho-ctaz-n61[^\"'\s]*\.png", html)
sig = ""
if img:
    try:
        h = get(img.group(0), "HEAD").headers
        sig = "|".join(str(h.get(k, "")) for k in ("ETag", "Content-Length", "Last-Modified"))
    except Exception as e:
        print("image not reachable:", e)
try:
    old = json.load(open(STATE))
except Exception:
    old = None
new = {"img": sig, "missing": missing}
json.dump(new, open(STATE, "w"))
changed = bool(missing) or (old is not None and old.get("img") and sig and old["img"] != sig)
print("state", new, "changed", changed)
if changed:
    title = "N61: el horario puede haber cambiado"
    body = (f"La página {PAGE} ya no coincide con el horario guardado en las apps "
            f"(faltan horas: {missing or 'ninguna'}; imagen de paradas cambiada: {bool(old and old.get('img') and sig and old['img'] != sig)}).\n\n"
            "Comprueba el horario oficial del CTAZ y actualiza N61 en las apps de Alagón y Casetas.")
    open_ = subprocess.run(["gh", "issue", "list", "--state", "open", "--search", title, "--json", "number"],
                           capture_output=True, text=True).stdout
    if not json.loads(open_ or "[]"):
        subprocess.run(["gh", "issue", "create", "--title", title, "--body", body])
