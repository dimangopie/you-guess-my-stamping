/* 你拼我猜 · PWA 外壳：全屏 / 安装 / 离线
   ─────────────────────────────────────────────
   ⚠ 这个项目可以在 file:// 下直接打开，而 file:// 下：
     · Service Worker 不执行
     · manifest 不生效
     · 安装提示不存在
   所以下面每一项都先判断再执行，任何失败都静默跳过 ——
   页面在两种打开方式下都必须一样能用。 */
(function () {
  "use strict";
  var HTTP = location.protocol === "http:" || location.protocol === "https:";


  /* ── ⓪ 站台导向图 · 客户端路由 ──────────────────────────────
     这个站点是多页的（14 个 HTML），所以路由**不做视图替换，只做派发**：
     哈希命中就跳过去；不命中就什么也不做，当前页照常渲染。

     两个用途：
       ① PWA 深链 —— manifest 的 start_url 是 index.html，
          所以 `index.html#/room` 要能进房间（安装到桌面后的快捷方式都走这条）
       ② 404 页拿同一张表给出路 —— 一张真的线路图，而不是两个按钮

     表放这里而不是 index.html：pwa.js 是**每个页面都加载**的应用外壳，
     放这儿才可能被 404 页共用；放 index.html 就只有落地页能用。
     「index.html 的路由」= index.html 是入口（dispatch 从它开始），
     而不是表只能写在它里面。 */
  var ROUTES = [
    ["index",   "index.html",   "站前招贴", "落地页"],
    ["login",   "login.html",   "办证处",   "登录 / 注册"],
    ["plaza",   "plaza.html",   "公告栏",   "广场 · 别人拼的题"],
    ["room",    "room.html",    "调度单",   "游戏房间"],
    ["compose", "compose.html", "制作单",   "拼图台（出题）"],
    ["guess",   "guess.html",   "猜题单",   "猜别人的题"],
    ["me",      "me.html",      "通行证",   "个人主页"],
    ["works",   "works.html",   "归档票根册", "个人作品"],
    ["banks",   "banks.html",   "目录册",   "词库"],
    ["issues",  "issues.html",  "整改台账", "评审问题台账"],
    ["404",     "404.html",     "查无此站", "错误页"],
    ["500",     "500.html",     "抢修通告", "错误页"],
    ["offline", "offline.html", "线路中断", "错误页"],
    ["full",    "full.html",    "限乘通告", "错误页"]
  ];
  var byKey = {};
  ROUTES.forEach(function (r) { byKey[r[0]] = r; });
  window.YPWC_ROUTES = ROUTES;          /* 给 404 页与调试用 */

  /* 把哈希解析成目标页 —— **纯函数，不跳转**。
     拆出来是为了可测：Firefox headless 的 --screenshot 抓不到
     「加载期就 location.replace」的页面（截图直接失败），
     所以跳转本身没法截图验证。有了这个纯函数，路由就能被断言。
     404 页也用它把哈希翻译成出路。 */
  function routeTo(key) {
    // ⚠ 原写法 .replace(/^#\/?/,"") 里 `#` 是必需的、`/` 才是可选的 ——
    //   于是 `#/room` 过、而裸写 `/room` 过不了（单元测试当场抓到）。
    //   正确是「# 可有可无、/ 也可有可无」，所以分两步剥，别用一个正则去表达两个可选。
    var h = String(key == null ? (location.hash || "") : key)
              .trim().replace(/^#/, "").replace(/^\//, "").toLowerCase();
    if (!h || !byKey[h]) return null;                 /* 认不到 → 不干预 */
    if (byKey[h][1] === location.pathname.split("/").pop()) return null;  /* 已在本页，别自跳 */
    return byKey[h][1];
  }
  window.YPWC_ROUTE_TO = routeTo;   /* 调试与 404 页共用 */

  function dispatch() {
    var to = routeTo();
    if (to) location.replace(to);
    return !!to;
  }
  // ⚠ 不套 if(HTTP)：跳转是纯前端行为，file:// 下一样成立。
  //   我第一版写成 if(HTTP) dispatch() 而注释写着「file:// 下也认」——
  //   注释与代码矛盾，路由在 file:// 下静默失效。
  dispatch();
  addEventListener("hashchange", dispatch);

  /* ── ① Service Worker（仅 http(s)）────────────────────── */
  if (HTTP && "serviceWorker" in navigator) {
    addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function () {});
    });
  }

  /* ── ② 全屏开关 ──────────────────────────────────────────
     两套前缀都留着：这个项目要跨平台，Safari 至今只认 webkit 那套。 */
  var el = document.documentElement;
  function fsEl() { return document.fullscreenElement || document.webkitFullscreenElement; }
  function req() {
    var f = el.requestFullscreen || el.webkitRequestFullscreen;
    if (f) { try { f.call(el); } catch (e) {} }
  }
  function exit() {
    var f = document.exitFullscreen || document.webkitExitFullscreen;
    if (f) { try { f.call(document); } catch (e) {} }
  }
  function supported() { return !!(el.requestFullscreen || el.webkitRequestFullscreen); }
  function toggle() { fsEl() ? exit() : req(); }
  function sync() {
    var on = !!fsEl();
    document.querySelectorAll("[data-fs]").forEach(function (b) {
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.title = on ? "退出全屏" : "全屏";
    });
  }
  ["fullscreenchange", "webkitfullscreenchange"].forEach(function (ev) {
    document.addEventListener(ev, sync);
  });

  /* 键盘：F 键切换（游戏里比找按钮快），Esc 交给浏览器 */
  addEventListener("keydown", function (e) {
    if (e.key !== "f" && e.key !== "F") return;
    var t = e.target;
    if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    e.preventDefault(); toggle();
  });

  /* ── ③ 安装 ──────────────────────────────────────────────
     Chrome/Edge 会发 beforeinstallprompt；Safari 不发，就没有按钮 ——
     不做「请点分享再点添加到主屏幕」那种说教浮层。 */
  var deferred = null;
  addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferred = e;
    document.querySelectorAll("[data-install]").forEach(function (b) { b.hidden = false; });
  });
  addEventListener("appinstalled", function () {
    deferred = null;
    document.querySelectorAll("[data-install]").forEach(function (b) { b.hidden = true; });
  });

  /* ── ④ 往导航里放按钮 ────────────────────────────────────
     注入而不是写 13 遍：只有一处要维护，也不会漏页。 */
  function mount() {
    var wrap = document.querySelector(".nav .wrap");   /* 导航的真实类名是 .nav，不是 .site-nav */
    if (!wrap || wrap.querySelector(".fs-btn")) return;

    if (supported()) {
      var fs = document.createElement("button");
      fs.type = "button";
      fs.className = "fs-btn";
      fs.setAttribute("data-fs", "");
      fs.setAttribute("aria-label", "全屏");
      fs.innerHTML = "<i></i>";
      fs.addEventListener("click", toggle);
      wrap.appendChild(fs);
    }

    var inst = document.createElement("button");
    inst.type = "button";
    inst.className = "fs-btn fs-install";
    inst.setAttribute("data-install", "");
    inst.hidden = true;
    inst.setAttribute("aria-label", "安装到桌面");
    inst.innerHTML = "<i></i>";
    inst.addEventListener("click", function () {
      if (!deferred) return;
      deferred.prompt();
      deferred.userChoice.then(function () { deferred = null; inst.hidden = true; });
    });
    wrap.appendChild(inst);

    sync();
  }
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", mount);
  else mount();
})();
