// Account page behaviour.
//
// Existing backend endpoints (docs/api.md):
//   GET  /api/users/me              the signed-in person's details
//   GET  /api/users/me/saved        their saved subjects and guides
//   POST /api/users/me/saved/remove remove a saved item
//   GET  /api/subjects              subject names for saved subject IDs
//
// NOT IN THE BACKEND YET - to be added by the backend owner. Until then the
// backend answers 404 and the forms say editing is not available yet.
//   POST /api/users/me/update
//     body: {"full_name", "email", "current_password"}
//     200: updated profile {"id", "email", "full_name", "created_at"}
//     400: {"error": ...} validation failed, or wrong current password
//     409: an account with the new email already exists
//   POST /api/users/me/password
//     body: {"current_password", "new_password"}  (same rule as sign up)
//     200: {"status": "updated"}
//     400: {"error": ...} validation failed, or wrong current password
//   Both: 401 when not signed in.
//
// Needs scripts/api.js loaded first.

(function () {
  "use strict";

  const loading = document.getElementById("account-loading");
  const loadError = document.getElementById("account-load-error");
  const content = document.getElementById("account-content");

  const NOT_AVAILABLE = "Editing your account isn't available yet. Please try again later.";
  const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  let subjectNames = {};

  // ---- Small helpers -----------------------------------------------------
  function showMessage(box, message) {
    box.querySelector("span").textContent = message;
    box.hidden = !message;
  }

  function setFieldError(input, message) {
    const field = input.closest(".field");
    let note = field.querySelector(".field-error");
    if (message) {
      if (!note) {
        note = document.createElement("p");
        note.className = "field-error";
        field.appendChild(note);
      }
      note.textContent = message;
      input.setAttribute("aria-invalid", "true");
    } else if (note) {
      note.remove();
      input.removeAttribute("aria-invalid");
    }
  }

  // Same rule as sign up and the backend: 12-128 characters, a number and a
  // symbol (anything that is not a letter, number or space).
  function passwordRuleOk(value) {
    const length = Array.from(value).length;
    return length >= 12 && length <= 128 &&
      /\p{N}/u.test(value) && /[^\p{L}\p{N}\s]/u.test(value);
  }

  // Message for a failed save. 404/405 means the endpoint isn't built yet.
  function saveProblem(result) {
    if (result && (result.status === 404 || result.status === 405)) return NOT_AVAILABLE;
    if (result && result.status === 400 && result.body && result.body.error &&
        result.body.error !== "Validation failed.") {
      return result.body.error; // e.g. "Password is incorrect."
    }
    if (result && result.status === 400) return "Some details weren't accepted. Check them and try again.";
    if (result && result.status === 401) return "Your session has ended. Log in again to make changes.";
    return apiProblemMessage(result);
  }

  function formatDate(iso) {
    const date = new Date(iso);
    if (isNaN(date)) return "";
    return date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  }

  // ---- Details -----------------------------------------------------------
  function showProfile(profile) {
    document.getElementById("detail-name").textContent = profile.full_name;
    document.getElementById("detail-email").textContent = profile.email;
    document.getElementById("detail-created").textContent = formatDate(profile.created_at);
    document.getElementById("edit-name").value = profile.full_name;
    document.getElementById("edit-email").value = profile.email;
    const navName = document.querySelector(".topnav .account-name");
    if (navName) navName.textContent = profile.full_name.trim().split(/\s+/)[0];
  }

  // ---- Saved subjects and guides ------------------------------------------
  const savedList = document.getElementById("saved-list");
  const savedEmpty = document.getElementById("saved-empty");
  const savedError = document.getElementById("saved-error");

  function itemLabel(item) {
    if (item.type === "subject") return subjectNames[item.id] || item.id;
    // Guide IDs are page slugs, e.g. "parents-guide" -> "Parents guide".
    const words = item.id.replace(/-/g, " ");
    return words.charAt(0).toUpperCase() + words.slice(1);
  }

  function showSaved(items) {
    savedList.replaceChildren();
    savedEmpty.hidden = items.length > 0;
    items.forEach(function (item) {
      const li = document.createElement("li");
      li.className = "saved-item";
      const text = document.createElement("span");
      const type = document.createElement("span");
      type.className = "saved-type";
      type.textContent = item.type === "subject" ? "Subject" : "Guide";
      const name = document.createElement("span");
      name.className = "saved-name";
      name.textContent = itemLabel(item);
      text.append(type, name);

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "saved-remove";
      remove.textContent = "Remove";
      remove.setAttribute("aria-label", "Remove " + itemLabel(item));
      remove.addEventListener("click", function () { removeSaved(item, remove); });

      li.append(text, remove);
      savedList.appendChild(li);
    });
  }

  async function removeSaved(item, button) {
    button.disabled = true;
    showMessage(savedError, "");
    let result = null;
    try {
      result = await apiRequest("POST", "/api/users/me/saved/remove", { type: item.type, id: item.id });
    } catch (e) { /* handled below */ }
    if (result && result.status === 200 && result.body && Array.isArray(result.body.items)) {
      showSaved(result.body.items);
      return;
    }
    button.disabled = false;
    showMessage(savedError, result && result.status === 401
      ? "Your session has ended. Log in again to make changes."
      : apiProblemMessage(result));
  }

  // ---- Edit details form --------------------------------------------------
  const detailsForm = document.getElementById("details-form");
  detailsForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const name = document.getElementById("edit-name");
    const email = document.getElementById("edit-email");
    const current = document.getElementById("edit-current-password");
    const errorBox = detailsForm.querySelector(".alert-error");
    const okBox = detailsForm.querySelector(".alert-success");
    showMessage(errorBox, "");
    showMessage(okBox, "");

    const nameValue = name.value.trim();
    const emailValue = email.value.trim();
    const checks = [
      [name, !nameValue ? "Enter your name." :
        Array.from(nameValue).length > 100 ? "Use 100 characters or fewer." : ""],
      [email, !emailValue ? "Enter your email address." :
        !EMAIL_PATTERN.test(emailValue) ? "Enter a valid email address." : ""],
      [current, current.value ? "" : "Enter your current password."],
    ];
    checks.forEach(function (c) { setFieldError(c[0], c[1]); });
    const firstBad = checks.find(function (c) { return c[1]; });
    if (firstBad) { firstBad[0].focus(); return; }

    const submit = detailsForm.querySelector("button[type=submit]");
    submit.disabled = true;
    let result = null;
    try {
      result = await apiRequest("POST", "/api/users/me/update", {
        full_name: nameValue, email: emailValue, current_password: current.value,
      });
    } catch (e) { /* handled below */ }
    submit.disabled = false;
    current.value = "";

    if (result && result.status === 200 && result.body && result.body.email) {
      showProfile(result.body);
      showMessage(okBox, "Your details have been updated.");
    } else if (result && result.status === 409) {
      setFieldError(email, "An account with this email already exists.");
      email.focus();
    } else {
      showMessage(errorBox, saveProblem(result));
    }
  });

  // ---- Change password form -----------------------------------------------
  const passwordForm = document.getElementById("password-form");
  passwordForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    const current = document.getElementById("pw-current");
    const next = document.getElementById("pw-new");
    const confirm = document.getElementById("pw-confirm");
    const errorBox = passwordForm.querySelector(".alert-error");
    const okBox = passwordForm.querySelector(".alert-success");
    showMessage(errorBox, "");
    showMessage(okBox, "");

    const checks = [
      [current, current.value ? "" : "Enter your current password."],
      [next, passwordRuleOk(next.value) ? "" : "Use 12 to 128 characters, including a number and a symbol."],
      [confirm, confirm.value && confirm.value === next.value ? "" : "Passwords do not match."],
    ];
    checks.forEach(function (c) { setFieldError(c[0], c[1]); });
    const firstBad = checks.find(function (c) { return c[1]; });
    if (firstBad) { firstBad[0].focus(); return; }

    const submit = passwordForm.querySelector("button[type=submit]");
    submit.disabled = true;
    let result = null;
    try {
      result = await apiRequest("POST", "/api/users/me/password", {
        current_password: current.value, new_password: next.value,
      });
    } catch (e) { /* handled below */ }
    submit.disabled = false;

    if (result && result.status === 200) {
      passwordForm.reset();
      showMessage(okBox, "Your password has been changed.");
    } else {
      current.value = "";
      showMessage(errorBox, saveProblem(result));
    }
  });

  // Clear a field's error as soon as it is edited.
  [detailsForm, passwordForm].forEach(function (form) {
    form.addEventListener("input", function (event) { setFieldError(event.target, ""); });
  });

  // ---- Load the page --------------------------------------------------------
  (async function load() {
    let me = null;
    try {
      me = await apiRequest("GET", "/api/users/me");
    } catch (e) { /* handled below */ }
    loading.hidden = true;

    // Not logged in: send them to create an account. 401 is the backend
    // saying "not signed in"; 404 means there is no backend at all (e.g.
    // Live Server), so nobody can be signed in either. replace() so the
    // Back button doesn't land on this page and bounce them again. The sign
    // up page links to Log in for people who already have an account.
    if (me && (me.status === 401 || me.status === 404)) {
      window.location.replace("Sign_up_page.html");
      return;
    }
    if (!me || me.status !== 200 || !me.body) {
      showMessage(loadError, apiProblemMessage(me));
      return;
    }

    showProfile(me.body);
    content.hidden = false;

    try {
      const [subjects, saved] = await Promise.all([
        apiRequest("GET", "/api/subjects"),
        apiRequest("GET", "/api/users/me/saved"),
      ]);
      if (subjects.status === 200 && subjects.body && Array.isArray(subjects.body.subjects)) {
        subjects.body.subjects.forEach(function (s) { subjectNames[s.id] = s.name; });
      }
      if (saved.status === 200 && saved.body && Array.isArray(saved.body.items)) {
        showSaved(saved.body.items);
      } else {
        showMessage(savedError, apiProblemMessage(saved));
      }
    } catch (e) {
      showMessage(savedError, apiProblemMessage(null));
    }
  })();
})();
