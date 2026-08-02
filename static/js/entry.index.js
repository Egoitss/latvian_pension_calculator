// Bundle entry for the simulator page.
//
// Imports every module index.html loads, in the order it loaded them,
// so top-level side effects still run in the same sequence. A
// module's own imports are evaluated before it either way, so the
// bundle behaves exactly as the eleven separate <script type="module">
// tags did.
//
// The source layout is unchanged: these are still separate ES modules
// and still what a developer edits. tools/build-js.sh turns this file
// into static/js/bundle/index.js, which is what production serves.
// app.INDEX_MODULES lists the same names for the no-bundle fallback,
// and tests/test_bundle.py fails if the two disagree.

import "./data.js";
import "./calc.js";
import "./chart.js";
import "./scenarios.js";
import "./ui.js";
import "./pension1.js";
import "./pension3.js";
import "./property.js";
import "./export.js";
import "./accordion.js";
import "./info.js";
