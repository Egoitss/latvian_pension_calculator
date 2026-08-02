"""The simulator's structured data.

One block, WebApplication, on the simulator itself. The names and the
description are the page's own title and meta description, so the
machine-readable copy says exactly what the visible page says.

No FAQPage: there is no FAQ on this site. FAQPage is a claim that the
questions and answers are on the page a visitor lands on, and
declaring one without them is a false statement that Google treats as
spam. Add the block when the FAQ block exists, not before.

40203754767 is the Latvian commercial register number, not a VAT
code, so it goes in ``identifier``; claiming a VAT registration we
cannot verify would be untrue.
"""
from __future__ import annotations

import json

ORIGIN = "https://pension.oats.lv"
LEGAL_NAME = 'SIA "OATS"'
CONTACT_EMAIL = "info@oats.lv"
REG_NR = "40203754767"

# Routes that describe an application. /loans is a separate tool and
# says nothing about itself yet.
APP_PATHS = ("/", "/en")

PUBLISHER = {
    "@type": "Organization",
    "name": LEGAL_NAME,
    "url": "https://oats.lv/",
    # The brand mark, 192x192 PNG. Google wants a raster logo of at
    # least 112px; the SVG favicon does not qualify.
    "logo": {
        "@type": "ImageObject",
        "url": "https://oats.lv/favicon-192.png",
        "width": 192,
        "height": 192,
    },
    "email": CONTACT_EMAIL,
    "identifier": {
        "@type": "PropertyValue",
        "name": "Latvijas komercreģistra numurs",
        "value": REG_NR,
    },
}


def web_application(lang: str, path: str, name: str,
                    description: str) -> dict:
    """The simulator as an application: free, browser-based, in the
    language of the page it is served on."""
    return {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": name,
        "description": description,
        "url": f"{ORIGIN}{path}",
        "applicationCategory": "FinanceApplication",
        "operatingSystem": "Web browser",
        "browserRequirements": "Requires JavaScript",
        "inLanguage": lang,
        "isAccessibleForFree": True,
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "EUR",
        },
        "publisher": PUBLISHER,
    }


def to_script(block: dict) -> str:
    """One JSON-LD body. ``<`` is escaped so a value containing
    ``</script>`` cannot close the tag early; the escape is still
    valid JSON."""
    return json.dumps(block, ensure_ascii=False,
                      indent=2).replace("<", "\\u003c")


def blocks_for(path: str, lang: str, name: str,
               description: str) -> list[str]:
    """Serialised blocks for one route; empty where nothing applies."""
    if path not in APP_PATHS:
        return []
    return [to_script(web_application(lang, path, name, description))]
