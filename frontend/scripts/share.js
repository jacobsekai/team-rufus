// Share buttons: <button class="share-button" data-share-title="...">.
//
// On phones and other devices with a share menu (the Web Share API) the
// button opens it, so people can send the page to a friend, parent or
// teacher in the app they already use. Elsewhere it copies the page link
// and says so. Nothing is posted on this website and nobody can message
// anyone through it, so there is nothing to moderate.

(function () {
  "use strict";

  function say(button, text) {
    const label = button.querySelector("span") || button;
    const original = button.dataset.shareLabel || label.textContent;
    button.dataset.shareLabel = original;
    label.textContent = text;
    window.setTimeout(function () { label.textContent = original; }, 2500);
  }

  async function copy(text) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    // Older browsers: copy from a hidden text box.
    const box = document.createElement("textarea");
    box.value = text;
    box.setAttribute("readonly", "");
    box.style.position = "fixed";
    box.style.opacity = "0";
    document.body.appendChild(box);
    box.select();
    const ok = document.execCommand("copy");
    box.remove();
    if (!ok) throw new Error("copy failed");
  }

  document.querySelectorAll(".share-button").forEach(function (button) {
    button.addEventListener("click", async function () {
      const url = window.location.href.split("#")[0];
      const title = button.dataset.shareTitle || document.title;
      if (navigator.share) {
        try {
          await navigator.share({ title: title, url: url });
        } catch (e) {
          // Closing the share menu without sharing is fine.
        }
        return;
      }
      try {
        await copy(url);
        say(button, "Link copied");
      } catch (e) {
        window.prompt("Copy this link:", url);
      }
    });
  });
})();
