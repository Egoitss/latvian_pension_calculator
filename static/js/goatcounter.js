/* goatcounter.js — GoatCounter config (was inline in base.html;
   external so the CSP allows no inline scripts). Host-prefixed path
   keeps pension.oats.lv distinct from oats.lv in one dashboard. */
window.goatcounter = {
  path: function (p) { return location.host + p; }
};
