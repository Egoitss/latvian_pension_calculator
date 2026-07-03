/* Back-link behaviour for the OATS nav (was an inline onclick,
   moved here so the CSP can drop 'unsafe-inline'): return to
   wherever the visitor came from; the href is the fallback when
   opened with no history (direct load / fresh tab). */
document.addEventListener("DOMContentLoaded", function () {
  var back = document.querySelector(".oats-back");
  if (!back) return;
  back.addEventListener("click", function (ev) {
    if (history.length > 1) {
      ev.preventDefault();
      history.back();
    }
  });
});
