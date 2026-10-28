// Accessibility page: text size, colour contrast and text to speech.
//
// The settings themselves live in scripts/display-settings.js (loaded in
// <head> on every page). This file only connects the page's radio
// buttons, summary, Test the voice and Reset buttons to them. Each choice
// applies to the whole site straight away, so the page itself is the live
// preview. Needs scripts/read-aloud.js loaded first.

(function () {
  "use strict";

  const settings = window.displaySettings;
  const groups = {
    textSize: "text-size",
    contrast: "contrast",
    readAloud: "read-aloud",
    speechRate: "speech-rate",
  };
  const summary = {
    textSize: document.getElementById("summary-text-size"),
    contrast: document.getElementById("summary-contrast"),
    readAloud: document.getElementById("summary-read-aloud"),
    speechRate: document.getElementById("summary-speech-rate"),
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

  // Browsers without speech: say so, and switch the choices off.
  if (!window.readAloud || !window.readAloud.supported) {
    document.getElementById("a11y-tts-unsupported").hidden = false;
    document.querySelectorAll('input[name="read-aloud"], input[name="speech-rate"], #a11y-tts-test')
      .forEach(function (control) { control.disabled = true; });
  }

  document.getElementById("a11y-tts-test").addEventListener("click", function () {
    window.readAloud.say("This is how the website sounds when it is read aloud.");
  });

  document.getElementById("a11y-reset").addEventListener("click", function () {
    show(settings.reset());
  });

  show(settings.load());
})();
