// Forum post page (forum-post.html?id=<post_id>): the full post, its
// comments and the comment form. Shared pieces and the API contract:
// scripts/forum.js.

(function () {
  "use strict";

  const f = window.forum;
  const thread = document.getElementById("thread");
  const crumb = document.getElementById("thread-crumb");
  const commentsSection = document.getElementById("comments");
  const heading = document.getElementById("comments-heading");
  const list = document.getElementById("comment-list");
  const form = document.getElementById("comment-form");
  const formError = document.getElementById("comment-error");
  const loginPrompt = document.getElementById("comment-login");
  const postId = new URLSearchParams(window.location.search).get("id");
  const postPath = "/api/forum/posts/" + encodeURIComponent(postId || "");
  let post = null;

  function backButton() {
    const back = f.el("a", "btn btn-outline", "Back to the forum");
    back.href = "forum.html";
    return back;
  }

  function showCount() {
    heading.textContent = f.countLabel(post.comment_count, "comment", "comments");
  }

  // ---------- The post ----------
  function postArticle() {
    const article = f.el("article", "forum-card forum-thread-post");
    const main = f.el("div", "forum-post-main");
    const title = f.el("h1", "forum-thread-title", post.title);
    const actions = f.el("div", "forum-actions");
    const comment = f.action("comment", "Comment");
    comment.addEventListener("click", async function () {
      if (!(await f.signedIn())) { window.location.href = f.loginUrl(); return; }
      text.focus();
      form.scrollIntoView({ block: "center", behavior: "smooth" });
    });
    actions.append.apply(actions, f.reactions(post, postPath));
    actions.append(comment, f.shareButton(post.id, post.title), f.reportButton("post", post.id));
    if (post.is_mine) {
      actions.append(f.deleteButton("post", postPath, function () {
        window.location.href = "forum.html";
      }));
    }
    main.append(f.meta(post), title, f.bodyText(post.body, "forum-body"), actions);
    article.append(main);
    return article;
  }

  // ---------- A comment ----------
  function commentItem(comment) {
    const item = f.el("li", "forum-comment");
    const path = "/api/forum/comments/" + encodeURIComponent(comment.id);
    const main = f.el("div", "forum-post-main");
    const actions = f.el("div", "forum-actions");
    actions.append.apply(actions, f.reactions(comment, path));
    actions.append(f.reportButton("comment", comment.id));
    if (comment.is_mine) {
      actions.append(f.deleteButton("comment", path, function () {
        item.remove();
        post.comment_count = Math.max(0, post.comment_count - 1);
        showCount();
      }));
    }
    main.append(f.meta(comment), f.bodyText(comment.body, "forum-body"), actions);
    item.append(main);
    return item;
  }

  // ---------- Load ----------
  async function load() {
    if (!postId) {
      thread.replaceChildren(f.stateBox("error", "We couldn't find that discussion",
        "The link may be incomplete.", backButton()));
      thread.setAttribute("aria-busy", "false");
      return;
    }
    thread.replaceChildren(f.stateBox("loading", "Loading the discussion\u2026"));
    let result = null;
    try { result = await apiRequest("GET", postPath); } catch (e) { /* below */ }
    thread.setAttribute("aria-busy", "false");

    if (result && f.isUnavailable(result)) {
      if (postId === f.EXAMPLE.post.id) showPreview();
      else thread.replaceChildren(f.unavailableBox());
      return;
    }
    if (result && result.status === 404) {
      thread.replaceChildren(f.stateBox("error", "This discussion isn't here any more",
        "It may have been deleted by the person who wrote it.", backButton()));
      return;
    }
    if (!result || result.status !== 200 || !result.body || !result.body.post) {
      thread.replaceChildren(f.stateBox("error", "We couldn't load this discussion", f.errorMessage(result), backButton()));
      return;
    }

    post = result.body.post;
    const comments = Array.isArray(result.body.comments) ? result.body.comments : [];
    post.comment_count = comments.length;
    document.title = post.title + " | Community forum | Team Rufus";
    crumb.textContent = post.title;
    thread.replaceChildren(postArticle());
    list.replaceChildren.apply(list, comments.map(commentItem));
    showCount();
    commentsSection.hidden = false;

    if (await f.signedIn()) {
      form.hidden = false;
    } else {
      document.getElementById("comment-login-link").href = f.loginUrl();
      loginPrompt.hidden = false;
    }
    if (window.location.hash === "#comments") commentsSection.scrollIntoView();
  }

  // ---------- Example discussion (backend not deployed yet) ----------
  function showPreview() {
    post = Object.assign({}, f.EXAMPLE.post);
    document.title = post.title + " | Community forum | Team Rufus";
    crumb.textContent = post.title;
    const article = postArticle();
    thread.replaceChildren(f.previewNote(), article);
    list.replaceChildren.apply(list, f.EXAMPLE.comments.map(function (c) {
      return commentItem(Object.assign({}, c));
    }));
    showCount();
    f.disableForPreview(thread);
    f.disableForPreview(list);
    commentsSection.hidden = false;
  }

  // ---------- New comment ----------
  const text = form.elements.body;
  f.counter(text, f.LIMITS.commentMax);
  text.addEventListener("input", function () { f.showFieldError(text, ""); });

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    formError.hidden = true;
    const body = text.value.trim();
    const problem = !body ? "Write a comment first."
      : body.length > f.LIMITS.commentMax ? "Keep your comment under " + f.LIMITS.commentMax + " characters." : "";
    f.showFieldError(text, problem);
    if (problem) { text.focus(); return; }

    const submit = form.querySelector('button[type="submit"]');
    submit.disabled = true;
    submit.textContent = "Posting\u2026";
    let result = null;
    try { result = await apiRequest("POST", postPath + "/comments", { body: body }); } catch (e) { /* below */ }
    submit.disabled = false;
    submit.textContent = "Comment";

    if (result && result.status === 201 && result.body) {
      form.reset();
      text.dispatchEvent(new Event("input"));
      const item = commentItem(result.body);
      list.append(item);
      post.comment_count += 1;
      showCount();
      item.scrollIntoView({ block: "nearest" });
      return;
    }
    if (result && result.status === 401) { window.location.href = f.loginUrl(); return; }
    formError.querySelector("span").textContent = result && result.status === 404
      ? "This discussion isn't here any more, so the comment couldn't be added."
      : f.errorMessage(result);
    formError.hidden = false;
  });

  load();
})();
