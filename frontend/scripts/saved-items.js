// Save buttons for subjects and guides.
//
// Any <button data-save-type="subject|guide" data-save-id="..."> becomes a
// Save / Saved toggle. It asks the backend which items are already saved
// (GET /api/users/me/saved), saves with POST /api/users/me/saved and
// un-saves with POST /api/users/me/saved/remove. Saved items show on the
// Account page. Logged-out visitors are sent to Log in when they press it.
// Buttons added later (e.g. the downloads list) call savedItems.bindAll().
// Needs scripts/api.js loaded first.

(function () {
  "use strict";

  const LABELS = {
    subject: { off: "Save subject", on: "Saved" },
    guide: { off: "Save", on: "Saved" },
  };

  let signedIn = null; // null until the first check
  let saved = new Set(); // "type:id"
  let loading = null;

  function load() {
    if (!loading) {
      loading = apiRequest("GET", "/api/users/me/saved").then(function (result) {
        signedIn = result.status === 200;
        saved = new Set();
        if (signedIn && result.body && Array.isArray(result.body.items)) {
          result.body.items.forEach(function (item) { saved.add(item.type + ":" + item.id); });
        }
      }).catch(function () {
        signedIn = false;
      });
    }
    return loading;
  }

  function show(button) {
    const type = button.dataset.saveType;
    const isSaved = saved.has(type + ":" + button.dataset.saveId);
    const label = button.querySelector("span") || button;
    label.textContent = (LABELS[type] || LABELS.guide)[isSaved ? "on" : "off"];
    button.setAttribute("aria-pressed", String(isSaved));
    button.classList.toggle("is-saved", isSaved);
  }

  async function toggle(button) {
    await load();
    if (!signedIn) {
      window.location.href = "Log_in_page.html";
      return;
    }
    const key = button.dataset.saveType + ":" + button.dataset.saveId;
    const body = { type: button.dataset.saveType, id: button.dataset.saveId };
    const path = saved.has(key) ? "/api/users/me/saved/remove" : "/api/users/me/saved";
    button.disabled = true;
    let result = null;
    try {
      result = await apiRequest("POST", path, body);
    } catch (e) { /* handled below */ }
    button.disabled = false;
    if (result && result.status === 401) {
      window.location.href = "Log_in_page.html";
      return;
    }
    if (result && (result.status === 200 || result.status === 201) && result.body && Array.isArray(result.body.items)) {
      saved = new Set(result.body.items.map(function (item) { return item.type + ":" + item.id; }));
      document.querySelectorAll("button[data-save-type]").forEach(show);
    } else {
      window.alert(result && result.status === 400 && result.body && result.body.error
        ? result.body.error
        : apiProblemMessage(result));
    }
  }

  function bindAll(root) {
    (root || document).querySelectorAll("button[data-save-type]:not([data-save-bound])").forEach(function (button) {
      button.dataset.saveBound = "true";
      button.addEventListener("click", function () { toggle(button); });
      load().then(function () { show(button); });
    });
  }

  bindAll(document);
  window.savedItems = { bindAll: bindAll };
})();
