// 서비스 워커 — 네트워크 우선, 오프라인일 때만 캐시로 폴백.
// 온라인이면 항상 최신 UI/데이터를 보여주고, 신호가 없을 땐 마지막 캐시를 보여준다.
const CACHE = "idea-dashboard-v5";
const SHELL = ["./", "./index.html", "./style.css", "./app.js", "./manifest.webmanifest"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  // 네트워크 우선: 성공하면 캐시 갱신, 실패(오프라인)하면 캐시 사용.
  e.respondWith(
    fetch(e.request)
      .then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match("./index.html")))
  );
});
