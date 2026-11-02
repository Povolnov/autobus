// Cloudflare Worker. Binding required: D1 database "autobus-visits" as DB.
const ORIGIN = "https://povolnov.github.io";
const cors = { "Access-Control-Allow-Origin": ORIGIN, "Access-Control-Allow-Methods": "POST", "Vary": "Origin" };

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "POST" || request.headers.get("Origin") !== ORIGIN) {
      return new Response("Not found", { status: 404 });
    }
    const country = request.cf?.country || "";
    ctx.waitUntil(env.DB.batch([
      env.DB.prepare("INSERT INTO visits (ip, country) VALUES ('', ?)").bind(country),
      env.DB.prepare("DELETE FROM visits WHERE ts < datetime('now', '-90 days')"),
    ]));
    return new Response(null, { status: 204, headers: cors });
  },
};
