/* 你拼我猜 · Service Worker
   ⚠ 只在 http(s) 下注册。file:// 打开时浏览器根本不执行 SW，
   所以 pwa.js 里也做了协议判断 —— 两条路都不会报错。

   策略：stale-while-revalidate。
   先给缓存（快、离线可用），同时后台拉新版本写回缓存 ——
   下次打开就是新的。比 cache-first 多一次网络，但不会「装了旧版就再也更新不了」。
   对这个项目尤其重要：页面是长期迭代的。 */

const CACHE = "ypwc-1guan51";
const SHELL = [
  "index.html",
  "base.css",
  "pwa.js",
  "manifest.webmanifest",
  "icon.svg",
  "icon-192.png",
  "icon-512.png",
  "icon-maskable-512.png",
  "404.html",
  "500.html",
  "banks.html",
  "compose.html",
  "full.html",
  "guess.html",
  "index.html",
  "login.html",
  "me.html",
  "offline.html",
  "plaza.html",
  "room.html",
  "works.html"
];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => c.addAll(SHELL))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())   /* 单个文件缺失不阻塞安装 */
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  if (new URL(req.url).origin !== location.origin) return;   /* 本项目的硬规矩：零外部资源 */

  e.respondWith(
    caches.open(CACHE).then(c =>
      c.match(req).then(hit => {
        const net = fetch(req).then(res => {
          if (res && res.ok) c.put(req, res.clone());
          return res;
        }).catch(() => hit);
        return hit || net;
      })
    )
  );
});
