// Euro formatting, one rule per locale. Mirror of money.py — the two
// must produce byte-identical output; tests/test_money.py checks both
// against the same table.
//
// Six modules each carried their own copy of
//   new Intl.NumberFormat("lv-LV", { style: "currency", ... })
// which is how the English build ended up showing Latvian grouping.
// The locale comes from <html lang> now, and the separators are written
// out rather than left to ICU, whose choice of space character for
// lv-LV differs between engines.
//
// Latvian: no grouping below five digits, so "1260 €" stays plain and
// only "105 300 €" is grouped, with a narrow no-break space. The comma
// is reserved for decimals. The symbol trails after a no-break space.
//
// English: ordinary thousands commas and a leading symbol, "€1,260".

const NARROW_NBSP = " ";
const NBSP = " ";
const EURO = "€";
const LV_MIN_DIGITS_TO_GROUP = 5;

// Insert `sep` every three digits from the right.
function group(digits, sep) {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, sep);
}

// The language the page is rendered in. Falls back to Latvian, which is
// the default locale on every OATS property.
export function pageLang() {
  return document.documentElement.lang === "en" ? "en" : "lv";
}

// Format `value` as euros. `lang` defaults to the page's own locale, so
// callers that never switch language do not have to pass it.
export function formatEur(value, { decimals = 0, lang } = {}) {
  const number = Number.isFinite(Number(value)) ? Number(value) : 0;
  const locale = lang || pageLang();
  const sign = number < 0 ? "-" : "";
  const text = Math.abs(number).toFixed(decimals);
  const [whole, frac] = text.split(".");

  if (locale === "en") {
    const body = decimals ? `${group(whole, ",")}.${frac}` : group(whole, ",");
    return `${sign}${EURO}${body}`;
  }

  let body = whole.length >= LV_MIN_DIGITS_TO_GROUP
    ? group(whole, NARROW_NBSP)
    : whole;
  if (decimals) body = `${body},${frac}`;
  return `${sign}${body}${NBSP}${EURO}`;
}

// Two decimals, for the loan and 3rd-pillar figures that need cents.
export function formatEurDecimal(value) {
  return formatEur(value, { decimals: 2 });
}
