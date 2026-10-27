// Top navigation: the menu button.
//
// Desktop: opens a small dropdown with Account, Accessibility and (when
// logged in) Log out.
// Small screens (see responsive.css): opens the stacked menu with the
// nav links, Account, Accessibility and the Log in / Sign up buttons.
// Either way this script toggles .is-open on the nav and keeps the
// button's accessible state (aria-expanded, label) in sync.
//
// The menu is only hidden once this script has run (it adds the
// .nav-js class), so the links still work if JavaScript fails.

(function () {
  "use strict";

  const nav = document.querySelector(".topnav");
  if (!nav) return;
  const toggle = nav.querySelector(".menu-toggle");
  if (!toggle) return;

  // Must match the breakpoint in responsive.css.
  const mobile = window.matchMedia("(max-width: 960px)");

  nav.classList.add("nav-js");

  function setOpen(open) {
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    // When logged in, the button shows the person's name, which is its
    // label (scripts/account-nav.js), so only label the icon version.
    if (!document.documentElement.classList.contains("signed-in")) {
      toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    }
  }

  toggle.addEventListener("click", function () {
    setOpen(!nav.classList.contains("is-open"));
  });

  // Clicking anywhere outside the nav closes the menu.
  document.addEventListener("click", function (event) {
    if (nav.classList.contains("is-open") && !nav.contains(event.target)) setOpen(false);
  });

  // Escape closes the menu and returns focus to the button.
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && nav.classList.contains("is-open")) {
      setOpen(false);
      toggle.focus();
    }
  });

  // Close the menu if the screen grows back to desktop size, so it is
  // not left open in the background.
  mobile.addEventListener("change", function (event) {
    if (!event.matches) setOpen(false);
  });
})();
