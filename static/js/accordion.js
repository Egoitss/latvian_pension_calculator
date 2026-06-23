// Generic accordion controller: cards expanded by default. A card opts
// out with data-accordion-collapsed (starts collapsed, expands on header
// click or when its trigger input receives a value).

// Read value from an input/select element as a number; empty → 0
function readValue(el) {
  if (!el) return 0;
  const raw = String(el.value ?? "").trim();
  if (raw === "") return 0;
  const n = parseFloat(raw);
  return Number.isFinite(n) ? n : 0;
}

// Setup one accordion card: handles click toggle + auto-expand on data
function initAccordion(card) {
  const triggerId = card.dataset.accordionTrigger;
  const trigger = triggerId ? document.getElementById(triggerId) : null;
  const header = card.querySelector(".accordion-header");

  // Expanded by default. Cards marked data-accordion-collapsed start
  // closed, but still auto-expand when their trigger holds a value.
  const optOut = card.hasAttribute("data-accordion-collapsed");
  if (!optOut || (trigger && readValue(trigger) > 0)) {
    card.classList.add("is-expanded");
  }

  // Manual click toggle on the header button
  if (header) {
    header.addEventListener("click", () => {
      card.classList.toggle("is-expanded");
    });
  }

  // One-shot auto-expand when the trigger receives a non-zero value
  if (trigger) {
    const onInput = () => {
      if (readValue(trigger) > 0 && !card.classList.contains("is-expanded")) {
        card.classList.add("is-expanded");
      }
    };
    trigger.addEventListener("input",  onInput);
    trigger.addEventListener("change", onInput);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-accordion]").forEach(initAccordion);
});
