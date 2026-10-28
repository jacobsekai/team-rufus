// Text to speech ("Read aloud"), switched on from the Accessibility page.
//
// Uses the browser's own speech (the Web Speech API), so nothing is sent
// to a server and it works without an account. When the setting is on, a
// small bar appears in the bottom-left corner of every page:
//   - "Read page" reads the page's main text one block at a time and
//     outlines the block being read, so it is easy to follow along.
//   - If some text is selected first, the button says "Read selection"
//     and reads just that.
//   - Pause / Resume and Stop. The Escape key also stops.
// Needs scripts/display-settings.js loaded first (in <head>). Load this
// with defer on every page.

(function () {
  "use strict";

  const settings = window.displaySettings;
  const synth = window.speechSynthesis;
  const supported = Boolean(settings && synth && window.SpeechSynthesisUtterance);

  const RATES = { slow: 0.8, normal: 1, fast: 1.25 };
  // Blocks of text worth reading, in page order.
  const BLOCKS = "h1, h2, h3, h4, h5, p, li, dt, dd, th, td, legend, label, summary, blockquote, figcaption";
  // Not content: menus, footer, the chat assistant and this bar.
  const SKIP = "nav, footer, script, style, noscript, [aria-hidden='true'], [hidden], " +
    "#rufus-chat-button, #rufus-chat-panel, .read-aloud-bar";

  let bar = null;
  let readButton, readLabel, pauseButton, stopButton;
  let queue = [];
  let reading = false;
  let highlighted = null;
  let selectionAtPress = "";

  function pickVoice() {
    const voices = synth.getVoices();
    return voices.find(function (v) { return v.lang === "en-GB"; }) ||
      voices.find(function (v) { return /^en/i.test(v.lang); }) ||
      null;
  }

  // Long utterances get cut off in some browsers, so read a sentence at a time.
  function sentences(text) {
    return text.match(/[^.!?]+[.!?]*["')\]]*\s*/g) || [text];
  }

  function selectedText() {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed) return "";
    if (bar && bar.contains(selection.anchorNode)) return "";
    return selection.toString().replace(/\s+/g, " ").trim();
  }

  function pageBlocks() {
    const root = document.querySelector("main") || document.body;
    const found = [];
    root.querySelectorAll(BLOCKS).forEach(function (el) {
      if (el.closest(SKIP)) return;
      if (!el.getClientRects().length) return; // not shown on screen
      // Already read as part of a bigger block (e.g. a <p> inside an <li>).
      if (found.some(function (block) { return block.el.contains(el); })) return;
      const text = el.innerText.replace(/\s+/g, " ").trim();
      if (text) found.push({ el: el, text: text });
    });
    return found;
  }

  function highlight(el) {
    if (highlighted) highlighted.classList.remove("read-aloud-current");
    highlighted = el;
    if (el) {
      el.classList.add("read-aloud-current");
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }

  function showState() {
    if (!bar) return;
    pauseButton.hidden = !reading;
    stopButton.hidden = !reading;
    pauseButton.textContent = synth.paused ? "Resume" : "Pause";
    pauseButton.setAttribute("aria-pressed", String(synth.paused));
    readLabel.textContent = selectedText() ? "Read selection" : "Read page";
  }

  function speakNext() {
    if (!reading) return;
    const item = queue.shift();
    if (!item) {
      stop();
      return;
    }
    if (item.el !== highlighted) highlight(item.el);
    const utterance = new SpeechSynthesisUtterance(item.text);
    const voice = pickVoice();
    if (voice) utterance.voice = voice;
    utterance.lang = voice ? voice.lang : "en-GB";
    utterance.rate = RATES[settings.load().speechRate] || 1;
    utterance.onend = speakNext;
    utterance.onerror = function (event) {
      // "interrupted"/"canceled" just mean Stop (or a new Read) was pressed.
      if (event.error !== "interrupted" && event.error !== "canceled") stop();
    };
    synth.speak(utterance);
  }

  // Reads a list of { el, text } blocks; el may be null (nothing to outline).
  function read(blocks) {
    synth.cancel();
    queue = [];
    blocks.forEach(function (block) {
      sentences(block.text).forEach(function (sentence) {
        if (sentence.trim()) queue.push({ el: block.el, text: sentence.trim() });
      });
    });
    reading = queue.length > 0;
    showState();
    speakNext();
  }

  function stop() {
    reading = false;
    queue = [];
    synth.cancel();
    highlight(null);
    showState();
  }

  function buildBar() {
    bar = document.createElement("div");
    bar.className = "read-aloud-bar";
    bar.setAttribute("role", "region");
    bar.setAttribute("aria-label", "Read aloud");
    bar.innerHTML =
      '<button type="button" class="read-aloud-read">' +
      '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      '<path d="M11 5 6 9H2v6h4l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/></svg>' +
      "<span>Read page</span></button>" +
      '<button type="button" class="read-aloud-pause read-aloud-secondary" hidden>Pause</button>' +
      '<button type="button" class="read-aloud-stop read-aloud-secondary" hidden>Stop</button>';
    readButton = bar.querySelector(".read-aloud-read");
    readLabel = readButton.querySelector("span");
    pauseButton = bar.querySelector(".read-aloud-pause");
    stopButton = bar.querySelector(".read-aloud-stop");

    // Clicking can clear the selection before "click" fires, so note it on press.
    readButton.addEventListener("pointerdown", function () {
      selectionAtPress = selectedText();
    });
    readButton.addEventListener("click", function () {
      const text = selectionAtPress || selectedText();
      selectionAtPress = "";
      read(text ? [{ el: null, text: text }] : pageBlocks());
    });
    pauseButton.addEventListener("click", function () {
      if (synth.paused) synth.resume();
      else synth.pause();
      showState();
    });
    stopButton.addEventListener("click", stop);
    document.body.appendChild(bar);
  }

  // The change event carries the new settings (they are saved just after).
  function update(event) {
    const current = (event && event.detail) || settings.load();
    const on = current.readAloud === "on";
    if (on && !bar) buildBar();
    if (!on && reading) stop();
    if (bar) bar.hidden = !on;
  }

  if (supported) {
    update();
    document.addEventListener("displaysettingschange", update);
    document.addEventListener("selectionchange", showState);
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && reading) stop();
    });
    // Don't keep talking about a page you've left.
    window.addEventListener("pagehide", function () { synth.cancel(); });
  }

  window.readAloud = {
    supported: supported,
    // Used by the Accessibility page's "Test the voice" button.
    say: function (text) {
      if (supported) read([{ el: null, text: text }]);
    },
  };
})();
