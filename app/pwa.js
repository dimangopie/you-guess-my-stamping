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
