/**
 * Timeline preview clock for QA framebuffer capture.
 * Reads window.TIMELINE_PREVIEW (injected by render_timeline.py).
 *
 * The clock keeps looping for the life of the page. ffmpeg -t on the host
 * decides how long to record — do not freeze here or the clip will be static.
 */
(function () {
  "use strict";

  const cfg = window.TIMELINE_PREVIEW || {};
  const loopSeconds = Math.max(1, Number(cfg.durationSeconds) || 90);
  const shouldLoop = cfg.loop !== false;
  const widgets = Array.from(document.querySelectorAll("[data-widget]"));
  const hud = document.getElementById("hud");
  const start = performance.now();

  function parseMs(el, attr, fallback) {
    const raw = el.getAttribute(attr);
    if (raw == null || raw === "") return fallback;
    const n = Number(raw);
    return Number.isFinite(n) ? n : fallback;
  }

  function setTransition(el, ms) {
    el.style.transitionDuration = `${Math.max(0, ms)}ms`;
  }

  function applyState(el, t) {
    const startS = parseMs(el, "data-start", 0);
    const durS = parseMs(el, "data-duration", 0);
    const endS = startS + durS;
    const tin = (el.getAttribute("data-transition-in") || "none").trim();
    const tout = (el.getAttribute("data-transition-out") || "none").trim();
    const tMs = parseMs(el, "data-transition-ms", 600);

    setTransition(el, tMs);

    const active = t >= startS && t < endS;
    const nearExit = active && tout === "fade" && t >= endS - tMs / 1000;

    el.classList.toggle("from-slideInLeft", tin === "slideInLeft");
    el.classList.toggle("from-slideInRight", tin === "slideInRight");
    el.classList.toggle("from-slideInUp", tin === "slideInUp");

    if (active && !nearExit) {
      el.classList.add("is-active");
      el.classList.remove("is-exit");
    } else if (nearExit) {
      el.classList.add("is-active", "is-exit");
    } else {
      el.classList.remove("is-active", "is-exit");
    }
  }

  function tick(now) {
    const elapsed = (now - start) / 1000;
    const t = shouldLoop ? elapsed % loopSeconds : Math.min(elapsed, loopSeconds);

    widgets.forEach((el) => applyState(el, t));
    if (hud) {
      hud.textContent = `t=${t.toFixed(1)}s / ${loopSeconds}s`;
    }
    requestAnimationFrame(tick);
  }

  requestAnimationFrame(tick);
})();
