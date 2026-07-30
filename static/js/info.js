// Disclosure controller for the ⓘ statistical footnotes.
//
// Five footnotes used to sit permanently under their fields as small grey
// text, which on a phone pushed the controls they explained off screen.
// Each is now a panel opened by the button that carries its id in
// aria-controls.
//
// The CSP here is script-src 'self', so this ships as a vendored file
// rather than an inline handler.

// Measure the panel's natural height. The panel animates between 0 and a
// pixel value, so the height has to come from the content wrapper, which
// is not itself clipped.
function naturalHeight(panel) {
  const inner = panel.querySelector(".pc-note-in");
  return inner ? inner.offsetHeight : 0;
}

// Open a panel: animate to the measured height, then release it to auto.
//
// Releasing matters because a panel inside a collapsed accordion measures
// 0 while hidden, and a frozen 0px would keep it clipped after the card
// opened. It also covers the note rewrapping when the window is resized.
function open(panel) {
  panel.dataset.open = "true";
  panel.style.height = naturalHeight(panel) + "px";
  panel.addEventListener("transitionend", function done(e) {
    if (e.propertyName !== "height" || panel.dataset.open !== "true") return;
    panel.style.height = "auto";
    panel.removeEventListener("transitionend", done);
  });
}

// Close a panel. Height is "auto" once open, which will not animate, so
// it is pinned to its current pixel height and the reflow forced before
// the collapse is set.
function close(panel) {
  panel.style.height = panel.getBoundingClientRect().height + "px";
  void panel.offsetHeight;
  panel.dataset.open = "false";
  panel.style.height = "0px";
}

// Toggle the panel a button points at, if the page still has it.
function toggle(button) {
  const panel = document.getElementById(button.getAttribute("aria-controls"));
  if (!panel) return;
  const willOpen = button.getAttribute("aria-expanded") !== "true";
  button.setAttribute("aria-expanded", String(willOpen));
  if (willOpen) open(panel);
  else close(panel);
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".pc-info").forEach((button) => {
    const panel = document.getElementById(button.getAttribute("aria-controls"));
    if (panel) {
      panel.dataset.open = "false";
      panel.style.height = "0px";
    }
    button.setAttribute("aria-expanded", "false");
    button.addEventListener("click", () => toggle(button));
  });
});
