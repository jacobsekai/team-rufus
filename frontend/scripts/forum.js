// Forum: shared pieces for forum.html (list) and forum-post.html (one post).
//
// Talks to the forum API in backend/forum.py (reference: docs/api.md,
// "Forum"). If the API isn't deployed yet it answers with its plain HTML
// 404 page, and both forum pages show "The forum isn't available yet"
// instead of breaking.
//
// Everything people write is shown with textContent, never innerHTML.
// Needs scripts/api.js and scripts/share.js loaded first.

(function () {
  "use strict";

  // Shown as a preview while the backend isn't deployed ("The forum isn't
  // live yet"). Same text as backend/forum_example.json: keep the two in step.
  const EXAMPLE = {
    "post": {
      "id": "example",
      "title": "Welcome to the T Level forum: introduce yourself!",
      "body": "Hi everyone, and welcome!\n\nThis is the place to ask questions and share what you know about T Levels: choosing a subject, what an industry placement is really like, and how to apply (including placements at Amazon).\n\nTo get things started, reply with a comment:\n- which T Level you're studying or thinking about\n- one question you'd like answered\n\nLike the posts and comments you find helpful so the best answers rise to the top, and use Share to send a discussion to a friend, parent or teacher.\n\nPlease keep it kind, and don't share personal details like your address or phone number. If you see something that breaks the rules, use Report and the team will check it.",
      "author_name": "Team Rufus",
      "created_at": "2026-11-03T09:00:00Z",
      "likes": 0,
      "dislikes": 0,
      "comment_count": 1,
      "my_vote": 0,
      "is_mine": false
    },
    "comments": [
      {
        "id": "example-comment-1",
        "body": "We'll start: lots of students ask whether placements are paid. It's up to each employer, so ask your school or college placement coordinator. There's more on the Information page too.",
        "author_name": "Team Rufus",
        "created_at": "2026-11-03T09:05:00Z",
        "likes": 0,
        "dislikes": 0,
        "my_vote": 0,
        "is_mine": false
      }
    ]
  };

  const REPORT_REASONS = {
    spam: "Spam or advertising",
    bullying: "Bullying or harassment",
    personal_info: "Shares personal information",
    other: "Something else",
  };

  const LIMITS = {
    titleMin: 5, titleMax: 120,
    bodyMin: 10, bodyMax: 5000,
    commentMax: 2000,
  };

  // The API answers an unknown path with Flask's HTML 404 page (no JSON),
  // and a missing post with a JSON 404. Only the first means "not built".
  function isUnavailable(result) {
    return result.status === 404 && result.body === null;
  }

  function errorMessage(result) {
    if (result && result.status === 429) {
      return "You're posting very quickly. Please wait a minute and try again.";
    }
    if (result && result.status === 400 && result.body && result.body.error) {
      const details = Array.isArray(result.body.details) ? " " + result.body.details.join(" ") : "";
      return result.body.error + details;
    }
    return apiProblemMessage(result);
  }

  // Log in page, then back to this page afterwards (scripts/login.js).
  function loginUrl() {
    const here = window.location.pathname.split("/").pop() + window.location.search;
    return "Log_in_page.html?next=" + encodeURIComponent(here);
  }

  let me = null;
  function signedIn() {
    if (!me) {
      me = apiRequest("GET", "/api/users/me")
        .then(function (result) { return result.status === 200; })
        .catch(function () { return false; });
    }
    return me;
  }

  // ---------- Small builders ----------
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  const timeFormat = new Intl.RelativeTimeFormat("en-GB", { numeric: "auto" });
  const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "long", timeStyle: "short" });
  const STEPS = [["year", 31536000], ["month", 2592000], ["week", 604800], ["day", 86400], ["hour", 3600], ["minute", 60]];

  function timeAgo(iso) {
    const date = new Date(iso);
    const node = el("time");
    if (isNaN(date)) return node;
    node.dateTime = date.toISOString();
    node.title = dateFormat.format(date);
    const seconds = (date - Date.now()) / 1000;
    const step = STEPS.find(function (s) { return Math.abs(seconds) >= s[1]; });
    node.textContent = step
      ? timeFormat.format(Math.round(seconds / step[1]), step[0])
      : "just now";
    return node;
  }

  // "Sam · 2 hours ago"
  function meta(item) {
    const line = el("p", "forum-meta");
    line.append(el("span", "forum-author", item.author_name || "Member"), " \u00b7 ", timeAgo(item.created_at));
    return line;
  }

  // Line breaks kept by CSS (white-space: pre-line); text never parsed as HTML.
  function bodyText(text, className) {
    return el("div", className, text || "");
  }

  function countLabel(n, one, many) {
    return n + " " + (n === 1 ? one : many);
  }

  // ---------- Like and dislike ----------
  const ICONS = {
    like: "M7 10v11M7 10l4-8a2 2 0 0 1 2 2v4h5.5a2 2 0 0 1 2 2.3l-1.3 7.5a2 2 0 0 1-2 1.7H7",
    dislike: "M17 14V3M17 14l-4 8a2 2 0 0 1-2-2v-4H5.5a2 2 0 0 1-2-2.3l1.3-7.5a2 2 0 0 1 2-1.7H17",
    comment: "M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z",
    share: "M4 12v7a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-7M16 6l-4-4-4 4M12 2v14",
  };
  function icon(name) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("width", "18");
    svg.setAttribute("height", "18");
    svg.setAttribute("aria-hidden", "true");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", ICONS[name]);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "currentColor");
    path.setAttribute("stroke-width", "2");
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    svg.append(path);
    return svg;
  }

  // An action button with an icon and a visible label or count.
  function action(name, text, className) {
    const button = el("button", "forum-action" + (className ? " " + className : ""));
    button.type = "button";
    button.append(icon(name), el("span", "", text));
    return button;
  }

  // Like and Dislike buttons with their counts. item has likes, dislikes
  // and my_vote (1, -1 or 0); path is "/api/forum/posts/<id>" or
  // "/api/forum/comments/<id>".
  function reactions(item, path) {
    const like = action("like", "", "forum-react forum-like");
    const dislike = action("dislike", "", "forum-react forum-dislike");

    function show() {
      like.lastChild.textContent = item.likes;
      dislike.lastChild.textContent = item.dislikes;
      like.setAttribute("aria-pressed", String(item.my_vote === 1));
      dislike.setAttribute("aria-pressed", String(item.my_vote === -1));
      like.setAttribute("aria-label", "Like, " + countLabel(item.likes, "like", "likes"));
      dislike.setAttribute("aria-label", "Dislike, " + countLabel(item.dislikes, "dislike", "dislikes"));
    }

    async function vote(value) {
      if (!(await signedIn())) { window.location.href = loginUrl(); return; }
      const before = { likes: item.likes, dislikes: item.dislikes, my_vote: item.my_vote };
      const next = item.my_vote === value ? 0 : value; // pressing again removes it
      // Show the change straight away; undo it if the server says no.
      item.likes += (next === 1) - (item.my_vote === 1);
      item.dislikes += (next === -1) - (item.my_vote === -1);
      item.my_vote = next;
      show();
      like.disabled = dislike.disabled = true;
      let result = null;
      try { result = await apiRequest("POST", path + "/vote", { value: next }); } catch (e) { /* below */ }
      like.disabled = dislike.disabled = false;
      if (result && result.status === 200 && result.body) {
        Object.assign(item, {
          likes: result.body.likes, dislikes: result.body.dislikes, my_vote: result.body.my_vote,
        });
      } else {
        Object.assign(item, before);
        if (result && result.status === 401) { window.location.href = loginUrl(); return; }
        window.alert(errorMessage(result));
      }
      show();
    }

    like.addEventListener("click", function () { vote(1); });
    dislike.addEventListener("click", function () { vote(-1); });
    show();
    return [like, dislike];
  }

  // ---------- Share ----------
  // Shares the post's own page (phone share menu, or copies the link).
  function shareButton(postId, title) {
    const button = action("share", "Share", "forum-share");
    button.addEventListener("click", function () {
      const url = new URL("forum-post.html?id=" + encodeURIComponent(postId), window.location.href).href;
      window.shareLink(button, url, title + " | Team Rufus forum");
    });
    return button;
  }

  // ---------- Report (one shared dialog) ----------
  let reportDialog = null;
  function buildReportDialog() {
    const dialog = el("dialog", "forum-dialog");
    dialog.setAttribute("aria-labelledby", "forum-report-title");
    const form = el("form");
    form.method = "dialog";
    form.append(el("h2", "forum-dialog-title", "Report this"));
    form.lastChild.id = "forum-report-title";
    form.append(el("p", "forum-hint", "Tell us what's wrong. Reports are private: the person won't know who sent it."));
    const fieldset = el("fieldset", "forum-reasons");
    fieldset.append(el("legend", "visually-hidden", "Reason"));
    Object.keys(REPORT_REASONS).forEach(function (key, i) {
      const label = el("label", "checkbox-label");
      const input = el("input");
      input.type = "radio";
      input.name = "reason";
      input.value = key;
      input.required = true;
      if (i === 0) input.checked = true;
      label.append(input, REPORT_REASONS[key]);
      fieldset.append(label);
    });
    const status = el("p", "forum-dialog-status");
    status.setAttribute("role", "status");
    const actions = el("div", "forum-dialog-actions");
    const cancel = el("button", "btn btn-outline", "Cancel");
    cancel.type = "button";
    cancel.addEventListener("click", function () { dialog.close(); });
    const send = el("button", "btn btn-primary", "Send report");
    send.type = "submit";
    actions.append(cancel, send);
    form.append(fieldset, status, actions);
    dialog.append(form);

    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      send.disabled = true;
      status.textContent = "Sending\u2026";
      let result = null;
      try {
        result = await apiRequest("POST", "/api/forum/reports", {
          type: dialog.dataset.type, id: dialog.dataset.id, reason: form.elements.reason.value,
        });
      } catch (e) { /* below */ }
      send.disabled = false;
      if (result && (result.status === 201 || result.status === 200)) {
        status.textContent = result.status === 201
          ? "Thanks. The team will review it."
          : "You've already reported this. Thanks.";
        setTimeout(function () { dialog.close(); }, 1200);
      } else if (result && result.status === 401) {
        window.location.href = loginUrl();
      } else {
        status.textContent = errorMessage(result);
      }
    });
    document.body.append(dialog);
    return dialog;
  }

  function reportButton(type, id) {
    const button = el("button", "forum-action forum-action-quiet", "Report");
    button.type = "button";
    button.addEventListener("click", async function () {
      if (!(await signedIn())) { window.location.href = loginUrl(); return; }
      reportDialog = reportDialog || buildReportDialog();
      reportDialog.dataset.type = type;
      reportDialog.dataset.id = id;
      reportDialog.querySelector(".forum-dialog-status").textContent = "";
      reportDialog.showModal();
    });
    return button;
  }

  // ---------- Delete (author only) ----------
  function deleteButton(label, path, onDeleted) {
    const button = el("button", "forum-action forum-action-quiet forum-action-danger", "Delete");
    button.type = "button";
    button.addEventListener("click", async function () {
      if (!window.confirm("Delete this " + label + "? This can't be undone.")) return;
      button.disabled = true;
      let result = null;
      try { result = await apiRequest("POST", path + "/delete", {}); } catch (e) { /* below */ }
      button.disabled = false;
      if (result && result.status === 200) onDeleted();
      else window.alert(errorMessage(result));
    });
    return button;
  }

  // ---------- Form helpers ----------
  function showFieldError(input, message) {
    const field = input.closest(".field");
    let error = field.querySelector(".field-error");
    if (!error) {
      error = el("p", "field-error");
      error.id = input.id + "-error";
      field.append(error);
    }
    error.textContent = message;
    error.hidden = !message;
    input.setAttribute("aria-invalid", String(Boolean(message)));
    if (message) input.setAttribute("aria-describedby", error.id);
    else input.removeAttribute("aria-describedby");
  }

  // "123 / 5000" under a textarea.
  function counter(textarea, max) {
    const note = textarea.closest(".field").querySelector(".forum-counter");
    function update() {
      note.textContent = textarea.value.length + " / " + max;
      note.classList.toggle("is-over", textarea.value.length > max);
    }
    textarea.addEventListener("input", update);
    update();
  }

  // ---------- Page states ----------
  // kind: loading | empty | unavailable | error
  function stateBox(kind, title, text, action) {
    const box = el("div", "forum-state forum-state-" + kind);
    box.setAttribute("role", kind === "error" ? "alert" : "status");
    box.append(el("h2", "forum-state-title", title));
    if (text) box.append(el("p", "", text));
    if (action) box.append(action);
    return box;
  }

  function unavailableBox() {
    return stateBox("unavailable", "The forum isn't available yet",
      "We're still building the place where posts are saved. Check back soon, or try the Ask about T Levels chat in the meantime.");
  }

  // "Not live yet" note above the example post.
  function previewNote() {
    const note = el("div", "forum-preview-note");
    note.setAttribute("role", "status");
    note.append(el("strong", "", "The forum isn't live yet."),
      " Here's an example of what a discussion will look like. Liking, commenting and posting open when it goes live.");
    return note;
  }

  // Example post: everything but Share is switched off.
  function disableForPreview(root) {
    root.querySelectorAll("button:not(.forum-share)").forEach(function (button) {
      button.disabled = true;
      button.title = "Available when the forum goes live";
    });
  }

  window.forum = {
    LIMITS: LIMITS,
    isUnavailable: isUnavailable,
    errorMessage: errorMessage,
    loginUrl: loginUrl,
    signedIn: signedIn,
    el: el,
    meta: meta,
    bodyText: bodyText,
    countLabel: countLabel,
    icon: icon,
    action: action,
    reactions: reactions,
    shareButton: shareButton,
    reportButton: reportButton,
    deleteButton: deleteButton,
    showFieldError: showFieldError,
    counter: counter,
    stateBox: stateBox,
    unavailableBox: unavailableBox,
    EXAMPLE: EXAMPLE,
    previewNote: previewNote,
    disableForPreview: disableForPreview,
  };
})();
