// Accessibility page: text size and colour contrast choices.
//
// The settings themselves live in scripts/display-settings.js (loaded in
// <head> on every page). This file only connects the page's radio
// buttons, summary and Reset button to them. Each choice applies to the
// whole site straight away, so the page itself is the live preview.

(function () {
  "use strict";

  const settings = window.displaySettings;
  const groups = { textSize: "text-size", contrast: "contrast" };
  const summary = {
    textSize: document.getElementById("summary-text-size"),
    contrast: document.getElementById("summary-contrast"),
  };

  function show(current) {
    Object.keys(groups).forEach(function (key) {
      const radio = document.querySelector(
        'input[name="' + groups[key] + '"][value="' + current[key] + '"]'
      );
      radio.checked = true;
      summary[key].textContent = settings.OPTIONS[key][current[key]];
    });
  }

  Object.keys(groups).forEach(function (key) {
    document.querySelectorAll('input[name="' + groups[key] + '"]').forEach(function (radio) {
      radio.addEventListener("change", function () {
        const change = {};
        change[key] = radio.value;
        show(settings.save(change));
      });
    });
  });

  document.getElementById("a11y-reset").addEventListener("click", function () {
    show(settings.reset());
  });

  show(settings.load());
})();
