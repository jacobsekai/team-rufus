// Text size, colour contrast and text to speech chosen on the
// Accessibility page.
//
// Load this in <head> WITHOUT defer on every page, so the saved choice is
// applied before the page is drawn (no flash of the default look). It sets
// data-text-size, data-contrast and data-read-aloud on <html>;
// styles/display-settings.css does the rest, and scripts/read-aloud.js
// shows the Read page button. The choice is kept in this browser only
// (localStorage), so it works without an account.

(function () {
  "use strict";

  const STORAGE_KEY = "rufus-display-settings";

  const OPTIONS = {
    textSize: {
      standard: "Standard (100%)",
      large: "Large (125%)",
      largest: "Largest (150%)",
    },
    contrast: {
      standard: "Standard",
      high: "High contrast",
      dark: "Dark",
    },
    readAloud: {
      off: "Off",
      on: "On",
    },
    speechRate: {
      slow: "Slow",
      normal: "Normal",
      fast: "Fast",
    },
  };
  const DEFAULTS = { textSize: "standard", contrast: "standard", readAloud: "off", speechRate: "normal" };

  // Unknown or missing values fall back to the default, so an old or
  // hand-edited saved value can never break the page.
  function clean(settings) {
    const result = {};
    Object.keys(DEFAULTS).forEach(function (key) {
      const value = settings && settings[key];
      result[key] = Object.prototype.hasOwnProperty.call(OPTIONS[key], value) ? value : DEFAULTS[key];
    });
    return result;
  }

  function load() {
    try {
      return clean(JSON.parse(localStorage.getItem(STORAGE_KEY)));
    } catch (e) {
      // Storage blocked (some private browsing modes) or not valid JSON.
      return clean(null);
    }
  }

  function apply(settings) {
    const root = document.documentElement;
    root.dataset.textSize = settings.textSize;
    root.dataset.contrast = settings.contrast;
    root.dataset.readAloud = settings.readAloud;
    // Lets scripts/read-aloud.js show or hide its button straight away.
    document.dispatchEvent(new CustomEvent("displaysettingschange", { detail: settings }));
  }

  function save(changes) {
    const settings = clean(Object.assign(load(), changes));
    apply(settings);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (e) {
      // Still applied to this page, just not remembered.
    }
    return settings;
  }

  function reset() {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) { /* nothing saved to remove */ }
    const settings = clean(null);
    apply(settings);
    return settings;
  }

  apply(load());
  // Keep other open tabs of the site in step with a change made here.
  window.addEventListener("storage", function (event) {
    if (event.key === STORAGE_KEY || event.key === null) apply(load());
  });

  window.displaySettings = {
    OPTIONS: OPTIONS,
    load: load,
    save: save,
    reset: reset,
  };
})();
