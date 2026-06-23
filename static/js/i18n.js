/* i18n.js — browser-side translation helper.
   Loaded as a plain (non-module) script so window.t is global and
   available to every ES module. Mirrors the server t(): returns the
   Latvian override when present, else the English source string. */
(function () {
  var LANG = window.LANG || "en";
  var MAP = window.I18N || {};
  // Collapse internal whitespace so lookups match catalog keys.
  function norm(s) { return String(s).replace(/\s+/g, " ").trim(); }
  // t(text) -> Latvian override (lv) or the English source (fallback).
  window.t = function (text) {
    if (LANG === "en") return text;
    var key = norm(text);
    return Object.prototype.hasOwnProperty.call(MAP, key)
      ? MAP[key] : text;
  };
})();
