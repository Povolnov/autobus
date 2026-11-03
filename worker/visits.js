// Cloudflare Worker. Binding required: D1 database "autobus-visits" as DB.
const ORIGIN = "https://povolnov.github.io";
const cors = { "Access-Control-Allow-Origin": ORIGIN, "Access-Control-Allow-Methods": "POST", "Vary": "Origin" };

export default {
  async scheduled(event, env, ctx) {
    const response = await fetch("https://api.github.com/repos/Povolnov/autobus/actions/workflows/update-trains.yml/dispatches", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "autobus-visits",
      },
      body: JSON.stringify({ ref: "main" }),
    });
    if (!response.ok) throw new Error(`GitHub returned ${response.status}`);
  },
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "POST" || request.headers.get("Origin") !== ORIGIN) {
      return new Response("Not found", { status: 404 });
    }
    const ip = request.headers.get("CF-Connecting-IP") || "";
    const country = request.cf?.country || "";
    const city = request.cf?.city || "";
    const body = (await request.text()).trim();
    const device = /^[0-9a-f-]{36}$/i.test(body) ? body.toLowerCase() : "";
    ctx.waitUntil(env.DB.batch([
      env.DB.prepare("INSERT INTO visits (ip, country, city, device_id) VALUES (?, ?, ?, ?)").bind(ip, country, city, device),
      env.DB.prepare("DELETE FROM visits WHERE ts < datetime('now', '-90 days')"),
    ]));
    return new Response(null, { status: 204, headers: cors });
  },
};
