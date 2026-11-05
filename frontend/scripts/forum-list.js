// Forum list page (forum.html): the posts, sorting, "Show more" and the
// new-post form (title and text). Shared pieces: scripts/forum.js. The
// chosen sort is kept in the address (forum.html?sort=top) so it can be shared.

(function () {
  "use strict";

  const f = window.forum;
  const list = document.getElementById("forum-list");
  const more = document.getElementById("forum-more");
  const sort = document.getElementById("forum-sort");
  const newButton = document.getElementById("forum-new");
  const compose = document.getElementById("forum-compose");
  const form = document.getElementById("compose-form");
  const formError = document.getElementById("compose-error");

  const params = new URLSearchParams(window.location.search);
  const state = {
    sort: params.get("sort") === "top" ? "top" : "new",
    cursor: null,
  };
  let posts = null; // the <ul>, once there is at least one post
  let latest = 0; // only the newest request may update the list
  let preview = false; // true while the forum API isn't deployed

  // ---------- One post in the list ----------
  function postCard(post) {
    const item = f.el("li");
    const card = f.el("article", "forum-post-card");
    const link = "forum-post.html?id=" + encodeURIComponent(post.id);

    const body = f.el("div", "forum-post-main");
    const title = f.el("h3", "forum-post-title");
    const titleLink = f.el("a", "", post.title);
    titleLink.href = link;
    title.append(titleLink);
    const excerpt = f.el("p", "forum-excerpt", post.body);

    const footer = f.el("div", "forum-actions");
    const comments = f.el("a", "forum-action");
    comments.href = link + "#comments";
    comments.append(f.icon("comment"), f.el("span", "", f.countLabel(post.comment_count || 0, "comment", "comments")));
    const path = "/api/forum/posts/" + encodeURIComponent(post.id);
    footer.append.apply(footer, f.reactions(post, path));
    footer.append(comments, f.shareButton(post.id, post.title), f.reportButton("post", post.id));
    if (post.is_mine) {
      footer.append(f.deleteButton("post", path, function () {
        item.remove();
        if (posts && !posts.children.length) showEmpty();
      }));
    }

    body.append(f.meta(post), title, excerpt, footer);
    card.append(body);
    item.append(card);
    return item;
  }

  function showEmpty() {
    const start = f.el("button", "btn btn-primary", "Add post");
    start.type = "button";
    start.addEventListener("click", openCompose);
    list.replaceChildren(f.stateBox("empty", "No discussions yet",
      "Be the first to ask a question or share what you know.", start));
    posts = null;
  }

  // ---------- Loading ----------
  async function load(reset) {
    const request = ++latest;
    if (reset) {
      state.cursor = null;
      posts = null;
      list.replaceChildren(f.stateBox("loading", "Loading discussions\u2026"));
    }
    list.setAttribute("aria-busy", "true");
    more.disabled = true;

    const query = new URLSearchParams({ sort: state.sort });
    if (state.cursor) query.set("cursor", state.cursor);

    let result = null;
    try { result = await apiRequest("GET", "/api/forum/posts?" + query); } catch (e) { /* below */ }
    if (request !== latest) return; // a different sort was chosen meanwhile
    list.setAttribute("aria-busy", "false");
    more.disabled = false;

    if (result && f.isUnavailable(result)) {
      // Backend not deployed yet: show the example post as a preview.
      const example = f.el("ul", "forum-posts");
      example.append(postCard(Object.assign({}, f.EXAMPLE.post)));
      f.disableForPreview(example);
      list.replaceChildren(f.previewNote(), example);
      // Sorting means nothing yet; Add post stays, to try the form.
      document.querySelector(".forum-sort").hidden = true;
      preview = true;
      more.hidden = true;
      return;
    }
    if (!result || result.status !== 200 || !result.body || !Array.isArray(result.body.posts)) {
      const retry = f.el("button", "btn btn-outline", "Try again");
      retry.type = "button";
      retry.addEventListener("click", function () { load(true); });
      list.replaceChildren(f.stateBox("error", "We couldn't load the forum", f.errorMessage(result), retry));
      more.hidden = true;
      return;
    }

    if (reset && !result.body.posts.length) {
      showEmpty();
    } else {
      if (!posts) {
        posts = f.el("ul", "forum-posts");
        list.replaceChildren(posts);
      }
      result.body.posts.forEach(function (post) { posts.append(postCard(post)); });
    }
    state.cursor = result.body.next_cursor || null;
    more.hidden = !state.cursor;
  }

  function rememberView() {
    const query = new URLSearchParams();
    if (state.sort !== "new") query.set("sort", state.sort);
    const search = query.toString();
    history.replaceState(null, "", search ? "?" + search : window.location.pathname);
  }

  // ---------- Sort ----------
  sort.value = state.sort;
  sort.addEventListener("change", function () {
    state.sort = sort.value;
    rememberView();
    load(true);
  });
  more.addEventListener("click", function () { load(false); });

  // ---------- New post ----------
  const title = form.elements.title;
  const text = form.elements.body;
  f.counter(text, f.LIMITS.bodyMax);
  [title, text].forEach(function (field) {
    field.addEventListener("input", function () { f.showFieldError(field, ""); });
  });

  async function openCompose() {
    // In the preview anyone may try the form (saving explains it isn't live).
    if (!preview && !(await f.signedIn())) { window.location.href = f.loginUrl(); return; }
    document.getElementById("compose-preview").hidden = !preview;
    compose.hidden = false;
    newButton.setAttribute("aria-expanded", "true");
    title.focus();
  }
  function closeCompose() {
    compose.hidden = true;
    newButton.setAttribute("aria-expanded", "false");
    newButton.focus();
  }
  newButton.addEventListener("click", function () {
    if (compose.hidden) openCompose(); else closeCompose();
  });
  document.getElementById("compose-cancel").addEventListener("click", closeCompose);

  function validate() {
    const L = f.LIMITS;
    const t = title.value.trim();
    const b = text.value.trim();
    const errors = [
      [title, t.length < L.titleMin ? "Write a title of at least " + L.titleMin + " characters."
        : t.length > L.titleMax ? "Keep the title under " + L.titleMax + " characters." : ""],
      [text, b.length < L.bodyMin ? "Write at least " + L.bodyMin + " characters."
        : b.length > L.bodyMax ? "Keep your post under " + L.bodyMax + " characters." : ""],
    ];
    errors.forEach(function (pair) { f.showFieldError(pair[0], pair[1]); });
    const first = errors.find(function (pair) { return pair[1]; });
    if (first) first[0].focus();
    return !first;
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    formError.hidden = true;
    if (!validate()) return;
    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    submit.textContent = "Posting\u2026";
    let result = null;
    try {
      result = await apiRequest("POST", "/api/forum/posts", {
        title: title.value.trim(), body: text.value.trim(),
      });
    } catch (e) { /* below */ }
    submit.disabled = false;
    submit.textContent = "Post";

    if (result && result.status === 201 && result.body) {
      form.reset();
      text.dispatchEvent(new Event("input"));
      closeCompose();
      if (!posts) {
        posts = f.el("ul", "forum-posts");
        list.replaceChildren(posts);
      }
      posts.prepend(postCard(result.body));
      posts.firstChild.querySelector(".forum-post-title a").focus();
      return;
    }
    if (result && result.status === 401) { window.location.href = f.loginUrl(); return; }
    formError.querySelector("span").textContent = result && f.isUnavailable(result)
      ? "The forum isn't available yet, so posts can't be saved."
      : f.errorMessage(result);
    formError.hidden = false;
  });

  // forum.html?new=1 (the Add post button on a discussion page) opens the
  // form straight away, once the page knows whether the forum is live.
  const opening = load(true);
  if (params.get("new") === "1") {
    opening.then(openCompose);
    params.delete("new");
    rememberView();
  }
})();
