/* ============================================================
   Team Rufus — Rufus peeks out of the logo's "C"
   Hovering (or keyboard-focusing) the top-left logo makes Rufus the
   corgi pop his head out of the hole in the "C". This script only adds
   the drawing; all motion lives in styles/rufus-peek.css.

   The SVG uses the logo image's own coordinates (viewBox 0 0 2000 2000,
   the PNG is 2000x2000), so the hole clip lines up with the C at any
   logo size. The overlay is laid over the image's content box (inside
   its padding) and re-measured on resize and before each hover.
   Decorative only: aria-hidden, no pointer events, no layout impact.
   ============================================================ */
(function () {
  "use strict";

  // The C's inner curve is close to a circle centred at (718, 778) with
  // a radius of 250 (logo image units). Rufus is visible inside that
  // circle (the hole) and anywhere above its centre line, so his neck
  // is hidden by the C's lower rim while his head pops out over the top.
  function rufusSvg(id) {
    return (
      '<svg viewBox="0 0 2000 2000" focusable="false" xmlns="http://www.w3.org/2000/svg">' +
      "<defs>" +
      '<clipPath id="' + id + '" clipPathUnits="userSpaceOnUse">' +
      '<path d="M468,778 A250,250 0 0 0 934,904 L934,778 L2400,778 L2400,-800 L-400,-800 L-400,778 Z"/>' +
      "</clipPath>" +
      "</defs>" +
      '<g clip-path="url(#' + id + ')">' +
      // A soft shadow inside the hole so it reads as an opening.
      '<ellipse class="rufus-hole" cx="718" cy="1000" rx="215" ry="70" fill="#0B2B57"/>' +
      '<g transform="translate(712 1085) scale(1.08)">' +
      '<g class="rufus-rise"><g class="rufus-squash"><g class="rufus-bob">' +
      // Neck and chest
      '<path d="M-205,120 C-212,-60 -182,-220 -112,-310 L112,-310 C182,-220 212,-60 205,120 Z" fill="#EB9A27"/>' +
      '<path d="M-128,120 C-138,-50 -98,-200 0,-270 C98,-200 138,-50 128,120 Z" fill="#FBE3C0"/>' +
      '<g class="rufus-head">' +
      // Ears (behind the head), each in its own group so they can flick
      '<g class="rufus-ear rufus-ear-left">' +
      '<path d="M-262,-590 C-312,-760 -306,-910 -250,-1010 C-176,-958 -104,-866 -66,-752 Z" fill="#F0A42C"/>' +
      '<path d="M-230,-640 C-262,-762 -258,-866 -230,-940 C-184,-898 -142,-834 -116,-760 Z" fill="#FCD9B0"/>' +
      "</g>" +
      '<g class="rufus-ear rufus-ear-right">' +
      '<path d="M262,-590 C312,-760 306,-910 250,-1010 C176,-958 104,-866 66,-752 Z" fill="#F0A42C"/>' +
      '<path d="M230,-640 C262,-762 258,-866 230,-940 C184,-898 142,-834 116,-760 Z" fill="#FCD9B0"/>' +
      "</g>" +
      // Head
      '<path d="M0,-815 C182,-815 296,-702 300,-548 C304,-420 238,-318 0,-298 C-238,-318 -304,-420 -300,-548 C-296,-702 -182,-815 0,-815 Z" fill="#F5B335"/>' +
      // Cream blaze down the forehead, cheeks and muzzle
      '<path d="M0,-770 C30,-770 42,-694 54,-604 C156,-590 270,-514 272,-424 C266,-338 152,-300 0,-298 C-152,-300 -266,-338 -272,-424 C-270,-514 -156,-590 -54,-604 C-42,-694 -30,-770 0,-770 Z" fill="#FBE3C0"/>' +
      // Eyebrow dots
      '<ellipse cx="-122" cy="-632" rx="24" ry="15" fill="#FBE3C0"/>' +
      '<ellipse cx="122" cy="-632" rx="24" ry="15" fill="#FBE3C0"/>' +
      // Eyes (look around + blink)
      '<g class="rufus-look">' +
      '<g class="rufus-eye"><circle cx="-120" cy="-548" r="40" fill="#2B1A12"/><circle cx="-132" cy="-562" r="12" fill="#FFFFFF"/></g>' +
      '<g class="rufus-eye"><circle cx="120" cy="-548" r="40" fill="#2B1A12"/><circle cx="108" cy="-562" r="12" fill="#FFFFFF"/></g>' +
      "</g>" +
      // Blush
      '<ellipse cx="-200" cy="-440" rx="40" ry="22" fill="#FF8F7A" opacity="0.45"/>' +
      '<ellipse cx="200" cy="-440" rx="40" ry="22" fill="#FF8F7A" opacity="0.45"/>' +
      // Muzzle, open smiling mouth and tongue
      '<ellipse cx="0" cy="-408" rx="128" ry="88" fill="#FFF3E2"/>' +
      '<path d="M-84,-396 C-66,-338 -34,-312 0,-312 C34,-312 66,-338 84,-396 C54,-380 26,-386 0,-402 C-26,-386 -54,-380 -84,-396 Z" fill="#6B2B23"/>' +
      '<g class="rufus-tongue">' +
      '<path d="M-40,-352 C-44,-296 -22,-262 0,-262 C22,-262 44,-296 40,-352 C20,-340 -20,-340 -40,-352 Z" fill="#FF7486"/>' +
      '<path d="M0,-342 L0,-296" stroke="#E0506A" stroke-width="8" stroke-linecap="round"/>' +
      "</g>" +
      '<path d="M-96,-404 C-70,-384 -30,-384 0,-404 C30,-384 70,-384 96,-404" fill="none" stroke="#3A2018" stroke-width="11" stroke-linecap="round"/>' +
      '<path d="M0,-428 L0,-402" stroke="#3A2018" stroke-width="11" stroke-linecap="round"/>' +
      // Nose
      '<path d="M-60,-472 C-60,-514 60,-514 60,-472 C60,-440 22,-420 0,-420 C-22,-420 -60,-440 -60,-472 Z" fill="#1E1410"/>' +
      '<ellipse cx="-20" cy="-490" rx="17" ry="9" fill="#FFFFFF" opacity="0.7"/>' +
      "</g>" + // .rufus-head
      "</g></g></g>" + // .rufus-bob, .rufus-squash, .rufus-rise
      "</g>" +
      "</g>" + // clip group
      // Sparkles that burst from the hole as he pops out
      '<g class="rufus-sparks" fill="#FF9900">' +
      '<path class="rufus-spark rufus-spark-1" d="M300,430 l26,-64 l26,64 l64,26 l-64,26 l-26,64 l-26,-64 l-64,-26 Z"/>' +
      '<path class="rufus-spark rufus-spark-2" d="M1110,420 l22,-54 l22,54 l54,22 l-54,22 l-22,54 l-22,-54 l-54,-22 Z" fill="#FFFFFF" stroke="#0057A8" stroke-width="14" stroke-linejoin="round"/>' +
      '<circle class="rufus-spark rufus-spark-3" cx="330" cy="760" r="34"/>' +
      '<circle class="rufus-spark rufus-spark-4" cx="1120" cy="720" r="30" fill="#0057A8"/>' +
      "</g>" +
      "</svg>"
    );
  }

  var count = 0;

  function place(link, img, peek) {
    var parent = peek.offsetParent;
    if (!parent) return; // hidden (display: none)
    var ir = img.getBoundingClientRect();
    var pr = parent.getBoundingClientRect();
    var cs = window.getComputedStyle(img);
    var padL = parseFloat(cs.paddingLeft) + parseFloat(cs.borderLeftWidth);
    var padT = parseFloat(cs.paddingTop) + parseFloat(cs.borderTopWidth);
    var padR = parseFloat(cs.paddingRight) + parseFloat(cs.borderRightWidth);
    var padB = parseFloat(cs.paddingBottom) + parseFloat(cs.borderBottomWidth);
    peek.style.left = ir.left - pr.left - parent.clientLeft + padL + "px";
    peek.style.top = ir.top - pr.top - parent.clientTop + padT + "px";
    peek.style.width = Math.max(0, ir.width - padL - padR) + "px";
    peek.style.height = Math.max(0, ir.height - padT - padB) + "px";
  }

  function init() {
    var links = document.querySelectorAll(".topnav .home-logo-link, .topnav .logo-link");
    Array.prototype.forEach.call(links, function (link) {
      var img = link.querySelector("img.logo");
      if (!img || link.querySelector(".rufus-peek")) return;
      count += 1;
      var peek = document.createElement("span");
      peek.className = "rufus-peek";
      peek.setAttribute("aria-hidden", "true");
      peek.innerHTML = rufusSvg("rufus-hole-clip-" + count);
      link.appendChild(peek);
      link.classList.add("has-rufus");
      var update = function () { place(link, img, peek); };
      update();
      img.addEventListener("load", update);
      window.addEventListener("resize", update);
      link.addEventListener("pointerenter", update);
      link.addEventListener("focusin", update);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
