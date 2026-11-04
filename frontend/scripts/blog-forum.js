// Blog page: the "Community forum" section with the newest discussions.
//
// Shows the 3 newest posts from the forum API (GET /api/forum/posts),
// with working Like and Dislike buttons. While the API isn't deployed it
// shows the example post as a preview instead. Uses the shared pieces in
// scripts/forum.js (load scripts/api.js, scripts/share.js and
// scripts/forum.js first).

(function () {
  "use strict";

  const f = window.forum;
  const list = document.getElementById("blog-forum-list");
  if (!f || !list) return;
  const SHOWN = 3;

  function card(post) {
    const item = f.el("li");
    const article = f.el("article", "forum-post-card");
    const link = "forum-post.html?id=" + encodeURIComponent(post.id);

    const title = f.el("h3", "forum-post-title");
    const titleLink = f.el("a", "", post.title);
    titleLink.href = link;
    title.append(titleLink);

    const actions = f.el("div", "forum-actions");
    actions.append.apply(actions, f.reactions(post, "/api/forum/posts/" + encodeURIComponent(post.id)));
    const comments = f.el("a", "forum-action");
    comments.href = link + "#comments";
    comments.append(f.icon("comment"), f.el("span", "", f.countLabel(post.comment_count || 0, "comment", "comments")));
    actions.append(comments);

    article.append(f.meta(post), title, f.el("p", "forum-excerpt", post.body), actions);
    item.append(article);
    return item;
  }

  function grid(posts) {
    const ul = f.el("ul", "forum-posts blog-forum-grid");
    posts.forEach(function (post) { ul.append(card(Object.assign({}, post))); });
    return ul;
  }

  function message(text) {
    const p = f.el("p", "blog-forum-message", text);
    p.setAttribute("role", "status");
    return p;
  }

  async function load() {
    let result = null;
    try { result = await apiRequest("GET", "/api/forum/posts?sort=new"); } catch (e) { /* below */ }
    list.setAttribute("aria-busy", "false");

    if (result && f.isUnavailable(result)) {
      const example = grid([f.EXAMPLE.post]);
      f.disableForPreview(example);
      list.replaceChildren(f.previewNote(), example);
      return;
    }
    if (!result || result.status !== 200 || !result.body || !Array.isArray(result.body.posts)) {
      list.replaceChildren(message("The latest discussions can't be loaded right now. Please try again later."));
      return;
    }
    const posts = result.body.posts.slice(0, SHOWN);
    list.replaceChildren(posts.length
      ? grid(posts)
      : message("No discussions yet. Be the first to ask a question with Add post."));
  }

  load();
})();
