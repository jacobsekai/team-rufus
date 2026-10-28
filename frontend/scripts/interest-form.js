// "Register your interest" form on the Amazon page.
//
// Checks the fields (same rules as the backend), then sends them to
// POST /api/expressions-of-interest. The list of placement areas comes
// from GET /api/subjects, so it only needs changing in one place; the
// areas written in the HTML are used if that request fails.
// Needs scripts/api.js loaded first.

(function () {
  "use strict";

  const form = document.getElementById("interest-form");
  if (!form) return;

  const fullName = form.querySelector("#interest-name");
  const email = form.querySelector("#interest-email");
  const customerType = form.querySelector("#interest-type");
  const school = form.querySelector("#interest-school");
  const consent = form.querySelector("#interest-consent");
  const areas = form.querySelector("#interest-areas");
  const submit = form.querySelector(".interest-submit");
  const success = document.getElementById("interest-success");
  const error = document.getElementById("interest-error");

  function setFieldError(input, message) {
    const field = input.closest(".interest-field");
    let note = field.querySelector(".interest-field-error");
    if (message) {
      if (!note) {
        note = document.createElement("p");
        note.className = "interest-field-error";
        field.appendChild(note);
      }
      note.textContent = message;
      input.setAttribute("aria-invalid", "true");
    } else if (note) {
      note.remove();
      input.removeAttribute("aria-invalid");
    }
  }

  function validate() {
    let ok = true;
    const name = fullName.value.trim();
    if (!name || name.length > 100) {
      setFieldError(fullName, name ? "Use 100 characters or fewer." : "Enter your full name.");
      ok = false;
    } else setFieldError(fullName, "");

    const address = email.value.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(address)) {
      setFieldError(email, address ? "Enter a valid email address." : "Enter your email address.");
      ok = false;
    } else setFieldError(email, "");

    if (!customerType.value) {
      setFieldError(customerType, "Choose who you are.");
      ok = false;
    } else setFieldError(customerType, "");

    if (school.value.trim().length > 200) {
      setFieldError(school, "Use 200 characters or fewer.");
      ok = false;
    } else setFieldError(school, "");

    if (!consent.checked) {
      setFieldError(consent, "Tick the box so we can store your details.");
      ok = false;
    } else setFieldError(consent, "");
    return ok;
  }

  // Placement areas from the backend's single list.
  apiRequest("GET", "/api/subjects").then(function (result) {
    if (result.status !== 200 || !result.body || !Array.isArray(result.body.subjects)) return;
    areas.replaceChildren();
    result.body.subjects.forEach(function (subject) {
      const label = document.createElement("label");
      label.className = "interest-check";
      const box = document.createElement("input");
      box.type = "checkbox";
      box.name = "interests";
      box.value = subject.id;
      label.append(box, " " + subject.name);
      areas.appendChild(label);
    });
  }).catch(function () { /* keep the areas written in the HTML */ });

  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    success.hidden = true;
    error.hidden = true;
    if (!validate()) {
      form.querySelector("[aria-invalid='true']").focus();
      return;
    }

    const body = {
      full_name: fullName.value.trim(),
      email: email.value.trim(),
      customer_type: customerType.value,
      interests: Array.from(form.querySelectorAll("input[name='interests']:checked"))
        .map(function (box) { return box.value; }),
      consent: true,
    };
    if (school.value.trim()) body.school = school.value.trim();

    submit.disabled = true;
    let result = null;
    try {
      result = await apiRequest("POST", "/api/expressions-of-interest", body);
    } catch (e) { /* handled below */ }
    submit.disabled = false;

    if (result && result.status === 201) {
      form.reset();
      success.hidden = false;
      success.focus();
      return;
    }
    error.querySelector("span").textContent =
      result && result.status === 400 && result.body && Array.isArray(result.body.details)
        ? result.body.details.join(" ")
        : apiProblemMessage(result);
    error.hidden = false;
  });
})();
