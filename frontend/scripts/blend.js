// Softens the edge where two light bands of a page meet (white and
// cream): a light band whose colour differs from the light band above
// gets a short gradient at its top, fading from the colour above into
// its own (styles/polish.css, .blend-top). Adapted from the
// team-rufus-copy design.
//
// Edges next to a dark band (the navy heroes and footer, and every band
// in the dark theme) stay crisp: a fade between dark and light passes
// through a muddy grey. In high contrast every band is white, so there
// is nothing to blend.
//
// The bands are the children of <main>, or of <body> on pages without
// one, so it works on both page styles.

(function () {
  "use strict";

  // Fade length, never longer than the band's own top padding, so the
  // fade stays clear of the content.
  const FADE = 96;
  const SKIP = "nav, footer, script, style, dialog, [hidden], .topnav";

  function opaque(colour) {
    const parts = colour.match(/[\d.]+/g);
    return parts && (parts.length < 4 || Number(parts[3]) > 0) ? parts.slice(0, 3).map(Number) : null;
  }

  function isDark(rgb) {
    return (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255 < 0.4;
  }

  // The element that paints a band's colour: a first child that covers
  // the whole band (her navy hero sits inside a white wrapper div, and
  // the navy is what shows), else the band itself, else a full-width
  // first child, falling back to the page behind it.
  function covers(child, band) {
    return child && child.offsetWidth >= band.offsetWidth - 1
      && child.offsetHeight >= band.offsetHeight - 1;
  }
  function painterOf(band) {
    let el = band;
    while (covers(el.firstElementChild, el) && opaque(getComputedStyle(el.firstElementChild).backgroundColor)) {
      el = el.firstElementChild;
    }
    if (el !== band) return { el: el, rgb: opaque(getComputedStyle(el).backgroundColor) };
    for (let depth = 0; el && depth < 3; depth += 1) {
      const rgb = opaque(getComputedStyle(el).backgroundColor);
      if (rgb) return { el: el, rgb: rgb };
      const child = el.firstElementChild;
      if (!child || child.offsetWidth < band.offsetWidth - 1 || child.offsetTop > band.offsetTop + 1) break;
      el = child;
    }
    for (let up = band.parentElement; up; up = up.parentElement) {
      const rgb = opaque(getComputedStyle(up).backgroundColor);
      if (rgb) return { el: band, rgb: rgb };
    }
    return { el: band, rgb: [255, 255, 255] };
  }

  function bands() {
    const root = document.querySelector("main") || document.body;
    return Array.from(root.children).filter(function (el) {
      return !el.matches(SKIP) && el.offsetHeight > 0
        && getComputedStyle(el).position !== "fixed";
    });
  }

  function blend() {
    document.querySelectorAll(".blend-top").forEach(function (el) {
      el.classList.remove("blend-top");
      el.style.removeProperty("--blend-from");
      el.style.removeProperty("--blend-size");
    });

    let above = null;
    bands().forEach(function (band) {
      const here = painterOf(band);
      if (above && here.rgb.join() !== above.rgb.join()
          && !isDark(here.rgb) && !isDark(above.rgb)
          && getComputedStyle(here.el).backgroundImage === "none") {
        const padding = parseFloat(getComputedStyle(here.el).paddingTop) || 0;
        const size = Math.min(FADE, Math.max(padding, 16));
        here.el.style.setProperty("--blend-from", "rgb(" + above.rgb.join(",") + ")");
        here.el.style.setProperty("--blend-size", size + "px");
        here.el.classList.add("blend-top");
      }
      above = here;
    });
  }

  blend();
  // Themes (Accessibility page) change the colours; screen size and text
  // size change the paddings.
  new MutationObserver(blend).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-contrast", "data-text-size"],
  });
  let timer = null;
  window.addEventListener("resize", function () {
    clearTimeout(timer);
    timer = setTimeout(blend, 150);
  });
})();
