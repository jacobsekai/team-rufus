// Top navigation: mobile menu.
//
// On small screens (see responsive.css) the nav links and the
// Log in / Sign up buttons are hidden behind the hamburger button.
// This script opens and closes that menu and keeps the button's
// accessible state (aria-expanded, label) in sync.
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
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  }

  toggle.addEventListener("click", function () {
    setOpen(!nav.classList.contains("is-open"));
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
