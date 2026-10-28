// Runs before the page is drawn: loaded in <head> WITHOUT defer, on purpose.
//
// If this browser tab already knows someone is logged in (scripts/
// account-nav.js saves their first name for the tab), mark the page
// straight away so the nav shows the logged-in version from the first
// frame, instead of showing Login / Sign up while the backend is asked.
// account-nav.js then checks with the backend and corrects it if needed.

try {
  if (sessionStorage.getItem("rufus.firstName")) {
    document.documentElement.classList.add("signed-in");
  }
} catch (e) {
  // Storage blocked (e.g. strict privacy settings): the nav updates after
  // the backend check instead.
}
