/* globals.js — hydrate window globals from inert JSON data blocks.
   Templates emit server data as
     <script type="application/json" data-global="NAME">…</script>
   which CSP treats as data (never executed), so script-src stays
   'self' with no inline scripts and no nonces. Must load before any
   script that reads the globals (i18n.js and the ES modules). */
(function () {
  var blocks = document.querySelectorAll(
    'script[type="application/json"][data-global]');
  for (var i = 0; i < blocks.length; i++) {
    var el = blocks[i];
    try {
      window[el.getAttribute("data-global")] =
        JSON.parse(el.textContent);
    } catch (e) {
      /* leave the global undefined; consumers have fallbacks */
    }
  }
})();
