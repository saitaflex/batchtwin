/* Shared session handling for every page.
 *
 * /app, /floor, /projections and /vera each had their own fetch wrapper, and
 * when the API moved behind authentication only /app was updated -- so the
 * other three silently died on 401. One implementation, used everywhere, is
 * what stops that happening again.
 */
(function () {
  const TOKEN_KEY = "bt_token";

  const token = () => localStorage.getItem(TOKEN_KEY) || "";

  const authHeaders = () => {
    const t = token();
    return t ? {Authorization: "Bearer " + t} : {};
  };

  /* No session -> send the operator to the login gate, remembering where they
     were trying to go. A blank screen is not an error message. */
  function requireSession(reason) {
    const back = encodeURIComponent(location.pathname + location.search);
    location.replace(`/app?next=${back}${reason ? "&reason=" + reason : ""}`);
  }

  async function api(url, body) {
    const opts = body
      ? {method: "POST",
         headers: {"Content-Type": "application/json", ...authHeaders()},
         body: JSON.stringify(body)}
      : {headers: authHeaders()};
    const r = await fetch(url, opts);
    if (r.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      requireSession("expired");
      // The browser is navigating away. Resolving would let the caller render
      // against undefined; rejecting would spray console errors on the way out.
      // Neither is useful, so this call simply never settles.
      return new Promise(() => {});
    }
    if (!r.ok) {
      const e = await r.json().catch(() => ({}));
      throw new Error(e.detail || `HTTP ${r.status}`);
    }
    return r.json();
  }

  /* Resolve who is signed in. Pages call this before rendering anything. */
  async function me() {
    if (!token()) { requireSession("none"); return null; }
    try {
      return await api("/api/me?token=" + encodeURIComponent(token()));
    } catch (e) { return null; }
  }

  window.bt = {TOKEN_KEY, token, authHeaders, api, me, requireSession};
})();
