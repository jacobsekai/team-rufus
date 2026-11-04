(function () {
  "use strict";

  const cards = document.querySelectorAll(".subjects-boxes > [class$='-box']");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  if (!cards.length || !("IntersectionObserver" in window) || reduceMotion.matches) {
    return;
  }

  const container = cards[0].parentElement;
  container.classList.add("is-revealing");

  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.12
  });

  cards.forEach(function (card) {
    observer.observe(card);
  });
})();
