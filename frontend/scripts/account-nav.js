// Nav bar: show who is logged in.
//
// Asks the backend who is signed in (GET /api/users/me). The backend
// checks the session cookie against the sessions table and loads the
// account from the users table, so the name only appears when it matches
// a stored account.
//
// To avoid a delay on every page, the first name is also remembered for
// this browser tab (sessionStorage). scripts/nav-early.js uses it to show
// the logged-in nav before the page is drawn, this script fills in the
// name straight away, and then the backend answer confirms or corrects it:
//   200          -> logged in (name refreshed)
//   401 or 404   -> not logged in (404 = no backend, e.g. Live Server)
//   other errors -> leave the nav as it is
//
// Logged in: the <html> element gets .signed-in. styles/menu.css then hides
// the Login / Sign up buttons and the menu icon, and the menu button shows
// the first name; it still opens the dropdown, which gains Log out.
//
// Needs scripts/api.js loaded first. rememberFirstName / forgetFirstName
// are also used by login.js, signup.js and account.js.

const FIRST_NAME_KEY = "rufus.firstName";

function firstNameOf(fullName) {
  return typeof fullName === "string" ? fullName.trim().split(/\s+/)[0] : "";
}

// Saves the first name for this tab and returns it ("" if none).
function rememberFirstName(fullName) {
  const name = firstNameOf(fullName);
  try {
    if (name) sessionStorage.setItem(FIRST_NAME_KEY, name);
  } catch (e) { /* storage blocked: the nav just updates a moment later */ }
  return name;
}

function forgetFirstName() {
  try { sessionStorage.removeItem(FIRST_NAME_KEY); } catch (e) { /* see above */ }
}

function rememberedFirstName() {
  try { return sessionStorage.getItem(FIRST_NAME_KEY) || ""; } catch (e) { return ""; }
}

(async function () {
  "use strict";

  const nav = document.querySelector(".topnav");
  const toggle = nav && nav.querySelector("button.menu-toggle");
  const logout = nav && nav.querySelector(".nav-logout");
  const nameLabel = toggle && toggle.querySelector(".account-name");
  if (!nameLabel || !logout) return;

  logout.addEventListener("click", async function () {
    logout.disabled = true;
    try {
      await apiRequest("POST", "/api/logout");
      forgetFirstName();
      window.location.href = "index.html";
    } catch (e) {
      logout.disabled = false;
      logout.textContent = "Couldn't log out. Try again.";
    }
  });

  function showSignedIn(name) {
    nameLabel.textContent = name; // textContent, never innerHTML: user input
    toggle.removeAttribute("aria-label"); // the visible name is the label
    logout.hidden = false;
    document.documentElement.classList.add("signed-in");
  }

  function showSignedOut() {
    document.documentElement.classList.remove("signed-in");
    nameLabel.textContent = "";
    logout.hidden = true;
    const open = toggle.getAttribute("aria-expanded") === "true";
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  }

  const remembered = rememberedFirstName();
  if (remembered) showSignedIn(remembered);

  let result;
  try {
    result = await apiRequest("GET", "/api/users/me");
  } catch (e) {
    return; // Network problem: leave the nav as it is.
  }

  if (result.status === 200 && result.body) {
    const name = rememberFirstName(result.body.full_name);
    if (name) showSignedIn(name);
  } else if (result.status === 401 || result.status === 404) {
    forgetFirstName();
    showSignedOut();
  }
})();
