// Log in page behaviour.
//
// Checks what was typed (email format, password filled in), then sends it
// to POST /api/login. The backend checks it against the account stored in
// the database and, if it matches, sets the session cookie. The red error
// message is only shown when the backend says the details are wrong, or
// when the request itself fails. Needs scripts/api.js loaded first.

(function () {
  "use strict";

  const form = document.getElementById("signin-form");
  if (!form) return;

  const email = form.querySelector("#email");
  const password = form.querySelector("#password");
  const rememberMe = form.querySelector("#remember-me");
  const submitButton = form.querySelector(".auth-submit");
  const errorAlert = document.querySelector(".alert-error");
  const errorText = errorAlert.querySelector("span");
  const WRONG_DETAILS = errorText.textContent;

  function showError(message) {
    errorText.textContent = message;
    errorAlert.hidden = false;
    errorAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // Lockout: the backend says how many seconds to wait (up to 15 minutes).
  function lockedMessage(seconds) {
    const minutes = Math.max(1, Math.ceil(seconds / 60));
    return "Too many wrong attempts. Wait " + minutes + " minute" + (minutes === 1 ? "" : "s") +
      " and try again.";
  }

  // ---- Password visibility toggles -------------------------------------
  // Works for any .field-toggle with a data-target pointing at an input id,
  // so the same code serves the sign-up page too.
  form.querySelectorAll(".field-toggle").forEach(function (toggle) {
    toggle.addEventListener("click", function () {
      const target = document.getElementById(toggle.dataset.target);
      if (!target) return;
      const show = target.type === "password";
      target.type = show ? "text" : "password";
      toggle.setAttribute("aria-label", show ? "Hide password" : "Show password");
      toggle.setAttribute("aria-pressed", String(show));
    });
  });

  // ---- Forgot password ---------------------------------------------------
  // Password reset needs email sending, which the prototype doesn't have
  // yet, so the link explains that instead of going nowhere.
  const forgotLink = document.getElementById("forgot-password");
  const forgotNote = document.getElementById("forgot-password-note");
  if (forgotLink && forgotNote) {
    forgotLink.addEventListener("click", function (event) {
      event.preventDefault();
      forgotNote.hidden = false;
    });
  }

  // ---- Inline field validation -----------------------------------------
  function setFieldError(input, message) {
    const field = input.closest(".field");
    if (!field) return;
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

  function validateEmail() {
    const value = email.value.trim();
    if (!value) {
      setFieldError(email, "Enter your email address.");
      return false;
    }
    // Deliberately light: the browser's type=email catches the rest, and we
    // don't want to reject unusual-but-valid addresses.
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      setFieldError(email, "Enter a valid email address.");
      return false;
    }
    setFieldError(email, "");
    return true;
  }

  function validatePassword() {
    if (!password.value) {
      setFieldError(password, "Enter your password.");
      return false;
    }
    setFieldError(password, "");
    return true;
  }

  // Clear a field's error as soon as the user starts fixing it.
  email.addEventListener("input", function () { setFieldError(email, ""); });
  password.addEventListener("input", function () { setFieldError(password, ""); });

  // ---- Submit ----------------------------------------------------------
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    errorAlert.hidden = true;

    const emailOk = validateEmail();
    const passwordOk = validatePassword();
    if (!emailOk || !passwordOk) {
      (emailOk ? password : email).focus();
      return;
    }

    // Stops double submits, which would count as two wrong attempts.
    submitButton.disabled = true;
    let result = null;
    try {
      result = await apiRequest("POST", "/api/login", {
        email: email.value.trim(),
        password: password.value,
        remember_me: rememberMe.checked,
      });
    } catch (e) {
      // Network failure: handled below as a general problem.
    }
    submitButton.disabled = false;

    if (result && result.status === 200) {
      // So the next page shows the name straight away (account-nav.js).
      if (result.body) rememberFirstName(result.body.full_name);
      window.location.href = "index.html";
      return;
    }
    if (result && result.status === 401) {
      showError(WRONG_DETAILS);
      password.value = "";
      password.focus();
    } else if (result && result.status === 429) {
      showError(lockedMessage(result.retryAfter));
    } else {
      showError(apiProblemMessage(result));
    }
  });
})();
