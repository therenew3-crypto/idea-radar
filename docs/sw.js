// 간단한 서비스 워커 — 앱 껍데기는 캐시 우선, 데이터는 네트워크 우선.
// 신호가 약해도 마지막으로 본 분석 결과를 보여줄 수 있다.
const CACHE = "idea-dashboard-v3";
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
  const url = new URL(e.request.url);
  // 분석 데이터(JSON): 네트워크 우선 → 실패 시 캐시
  if (url.pathname.includes("/data/")) {
    e.respondWith(
      fetch(e.request)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
          return res;
        })
        .catch(() => caches.match(e.request))
    );
    return;
  }
  // 그 외(앱 껍데기): 캐시 우선 → 없으면 네트워크
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
