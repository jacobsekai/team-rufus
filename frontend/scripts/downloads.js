// "Guides to download" list on the Information page.
//
// Gets the list from GET /api/content and shows one card per guide.
// Each download is a normal link to /api/content/<id>/download, which
// redirects to a file link that works for 5 minutes. Guides marked
// requires_login show "Log in to download" until the visitor is signed in.
// Signed-in visitors also get a Save button (scripts/saved-items.js).
// Needs scripts/api.js and scripts/saved-items.js loaded first.

(async function () {
  "use strict";

  const list = document.getElementById("download-list");
  const status = document.getElementById("downloads-status");
  if (!list) return;

  let result = null;
  try {
    result = await apiRequest("GET", "/api/content");
  } catch (e) { /* handled below */ }

  if (!result || result.status !== 200 || !result.body || !Array.isArray(result.body.items)) {
    status.textContent = result && result.status === 403
      ? apiProblemMessage(result)
      : "The guides can't be loaded right now. Please try again later.";
    return;
  }

  const signedIn = result.body.signed_in === true;
  status.hidden = true;

  result.body.items.forEach(function (item) {
    const card = document.createElement("li");
    card.className = "download-card";

    const title = document.createElement("h3");
    title.textContent = item.title;
    card.appendChild(title);

    if (item.requires_login) {
      const badge = document.createElement("p");
      badge.className = "download-badge";
      badge.textContent = "Account holders only";
      card.appendChild(badge);
    }

    const description = document.createElement("p");
    description.textContent = item.description || "";
    card.appendChild(description);

    const actions = document.createElement("div");
    actions.className = "download-actions";
    const link = document.createElement("a");
    if (item.requires_login && !signedIn) {
      link.className = "btn btn-outline";
      link.href = "Log_in_page.html";
      link.textContent = "Log in to download";
    } else {
      link.className = "btn btn-primary";
      link.href = item.download_url;
      link.textContent = "Download";
      link.setAttribute("aria-label", "Download " + item.title);
    }
    actions.appendChild(link);

    if (signedIn) {
      const save = document.createElement("button");
      save.type = "button";
      save.className = "btn btn-outline";
      save.dataset.saveType = "guide";
      save.dataset.saveId = item.id;
      save.textContent = "Save";
      actions.appendChild(save);
    }
    card.appendChild(actions);
    list.appendChild(card);
  });

  if (window.savedItems) window.savedItems.bindAll(list);
})();
