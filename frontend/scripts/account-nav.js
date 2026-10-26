// Nav bar: show who is logged in.
//
// Asks the backend who is signed in (GET /api/users/me). The backend
// checks the session cookie against the sessions table and loads the
// account from the users table, so the name only appears when it matches
// a stored account. Not signed in, or any error: the nav stays as it is.
//
// If signed in, adds .is-signed-in to the nav. styles/menu.css then hides
// the Login / Sign up buttons and the menu icon, and the menu button shows
// the first name; it still opens the dropdown, which gains a Log out item.
// Every page has the same menu button and dropdown (see styles/menu.css).
//
// Needs scripts/api.js loaded first.

(async function () {
  "use strict";

  const nav = document.querySelector(".topnav");
  if (!nav) return;

  let result;
  try {
    result = await apiRequest("GET", "/api/users/me");
  } catch (e) {
    return; // Network problem: leave the nav as it is.
  }
  if (result.status !== 200 || !result.body || typeof result.body.full_name !== "string") return;

  const firstName = result.body.full_name.trim().split(/\s+/)[0];
  if (!firstName) return;

  const toggle = nav.querySelector("button.menu-toggle");
  const logout = nav.querySelector(".nav-logout");
  if (toggle && logout) showNameAsMenuButton(toggle, logout, firstName);

  function showNameAsMenuButton(menuButton, logoutButton, name) {
    // textContent, never innerHTML: the name is user input.
    menuButton.querySelector(".account-name").textContent = name;
    menuButton.removeAttribute("aria-label"); // the visible name is the label
    nav.classList.add("is-signed-in");

    logoutButton.hidden = false;
    logoutButton.addEventListener("click", async function () {
      logoutButton.disabled = true;
      try {
        await apiRequest("POST", "/api/logout");
        window.location.href = "index.html";
      } catch (e) {
        logoutButton.disabled = false;
        logoutButton.textContent = "Couldn't log out. Try again.";
      }
    });
  }
})();
