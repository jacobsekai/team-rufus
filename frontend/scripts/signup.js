// Sign up page behaviour.
//
// Checks what was typed using the same rules as the backend, then sends it
// to POST /api/users. The backend stores the account in the database (the
// password is hashed, never stored as typed) and signs the new user in.
// Needs scripts/api.js loaded first.

(function () {
  "use strict";

  const form = document.getElementById("signup-form");
  if (!form) return;

  const fullName = form.querySelector("#full-name");
  const email = form.querySelector("#email");
  const password = form.querySelector("#password");
  const confirm = form.querySelector("#confirm-password");
  const acceptTerms = form.querySelector("#accept-terms");
  const submitButton = form.querySelector(".auth-submit");
  const errorAlert = document.querySelector(".alert-error");
  const errorText = errorAlert.querySelector("span");

  function showError(message) {
    errorText.textContent = message;
    errorAlert.hidden = false;
    errorAlert.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  // ---- Password visibility toggles -------------------------------------
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

  // Same rule as the backend (backend/accounts.py): 12 to 128 characters,
  // with a number and a symbol. A symbol is anything that is not a letter,
  // number or space. Lengths count characters, like the backend does.
  function passwordRuleOk(value) {
    const length = Array.from(value).length;
    return length >= 12 && length <= 128 &&
      /\p{N}/u.test(value) && /[^\p{L}\p{N}\s]/u.test(value);
  }

  const validators = {
    name: function () {
      if (!fullName.value.trim()) { setFieldError(fullName, "Enter your name."); return false; }
      if (Array.from(fullName.value.trim()).length > 100) {
        setFieldError(fullName, "Use 100 characters or fewer."); return false;
      }
      setFieldError(fullName, ""); return true;
    },
    email: function () {
      const v = email.value.trim();
      if (!v) { setFieldError(email, "Enter your email address."); return false; }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) { setFieldError(email, "Enter a valid email address."); return false; }
      setFieldError(email, ""); return true;
    },
    password: function () {
      if (!passwordRuleOk(password.value)) {
        setFieldError(password, "Use 12 to 128 characters, including a number and a symbol.");
        return false;
      }
      setFieldError(password, ""); return true;
    },
    confirm: function () {
      if (confirm.value !== password.value || !confirm.value) {
        setFieldError(confirm, "Passwords do not match.");
        return false;
      }
      setFieldError(confirm, ""); return true;
    },
    terms: function () {
      if (!acceptTerms.checked) {
        setFieldError(acceptTerms, "Tick to agree to the Terms of use and Privacy notice.");
        return false;
      }
      setFieldError(acceptTerms, ""); return true;
    },
  };

  [fullName, email, password, confirm].forEach(function (input) {
    input.addEventListener("input", function () { setFieldError(input, ""); });
  });
  acceptTerms.addEventListener("change", function () { setFieldError(acceptTerms, ""); });

  // ---- Submit ----------------------------------------------------------
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    errorAlert.hidden = true;

    const results = [validators.name(), validators.email(), validators.password(),
      validators.confirm(), validators.terms()];
    if (!results.every(Boolean)) {
      const firstInvalid = [fullName, email, password, confirm, acceptTerms].find(function (el) {
        return el.getAttribute("aria-invalid") === "true";
      });
      if (firstInvalid) firstInvalid.focus();
      return;
    }

    submitButton.disabled = true;
    let result = null;
    try {
      result = await apiRequest("POST", "/api/users", {
        full_name: fullName.value.trim(),
        email: email.value.trim(),
        password: password.value,
        accept_terms: true,
      });
    } catch (e) {
      // Network failure: handled below as a general problem.
    }
    submitButton.disabled = false;

    // 201: account saved and the user is signed in.
    if (result && result.status === 201) {
      window.location.href = "index.html";
      return;
    }
    if (result && result.status === 409) {
      setFieldError(email, "An account with this email already exists. Log in instead.");
      email.focus();
    } else if (result && result.status === 400) {
      // The checks above match the backend, so this should be rare.
      showError("Some details weren't accepted. Check them and try again.");
    } else {
      showError(apiProblemMessage(result));
    }
  });
})();
