/* loans_prefill.js — pre-fill the P2L balance from a ?p2l= query
   param (was inline in loans.html; external so the CSP allows no
   inline scripts). */
(function () {
  var params = new URLSearchParams(window.location.search);
  var v = params.get("p2l");
  if (v) {
    var el = document.getElementById("p2lBalance");
    if (el) { el.value = v; el.dispatchEvent(new Event("input")); }
  }
})();
