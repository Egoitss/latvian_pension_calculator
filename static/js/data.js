// Domain constants — mirrors data.py; keep in sync when updating plan data
export const CONSTANTS = {
  VSAOI_CEILING: 105_300,
  P2L_RATE: 0.06,
  DEFAULT_RETURN: 8.0,
  PENSION_TAX_FREE_THRESHOLD: 1_000,
  PENSION_TAX_RATE: 0.255,
};

// Latvia 2023 — cumulative survival probability from age 67
// [years_elapsed, probability] — source: CSP Latvia IRP020 / Eurostat demo_mlexpec
export const SURVIVAL_FROM_67 = {
  men:   [[0, 1.00], [3, 0.843], [8, 0.652], [13, 0.451], [18, 0.300], [25, 0.150]],
  women: [[0, 1.00], [3, 0.929], [8, 0.809], [13, 0.657], [18, 0.510], [25, 0.330]],
};

// Latvia 2023 — probability that a person aged X survives to reach age 67
// [current_age, probability] — derived from Eurostat demo_mlifetable Latvia 2022–2023
export const SURVIVAL_TO_67 = {
  men: [
    [25, 0.64], [30, 0.66], [35, 0.68], [40, 0.71],
    [45, 0.75], [50, 0.80], [55, 0.85], [60, 0.91],
    [65, 0.96], [67, 1.00],
  ],
  women: [
    [25, 0.87], [30, 0.88], [35, 0.89], [40, 0.90],
    [45, 0.92], [50, 0.93], [55, 0.95], [60, 0.97],
    [65, 0.99], [67, 1.00],
  ],
};

// Remaining life expectancy e(x) at key ages — Latvia 2023 (CSP IRP020)
export const LIFE_EXPECTANCY_LV = {
  men:   { 65: 14.3, 67: 13.3, 70: 11.9, 75: 9.5, 80: 7.3, 85: 5.4 },
  women: { 65: 19.2, 67: 17.7, 70: 15.6, 75: 12.3, 80: 9.3, 85: 6.8 },
};

// Effective divisor (months) for mūža pensija annuity pricing.
// Mirrors data.py ANNUITY_DIVISOR. monthly ≈ capital / ANNUITY_DIVISOR[g][age]
export const ANNUITY_DIVISOR = {
  male:   { 62: 209, 63: 202, 64: 196, 65: 189, 66: 183, 67: 176, 68: 169, 69: 162 },
  female: { 62: 284, 63: 273, 64: 264, 65: 253, 66: 244, 67: 234, 68: 224, 69: 215 },
};

// Pension plan dataset — matches data.py PLANS list (snake_case keys)
export const PLANS = [
  // Custom manual entry
  {
    category: "Custom", name: "Manuāls pieņēmums",
    return_3y: 8, return_5y: 8, manual: true,
  },

  // Market benchmark long-run assumptions
  { category: "Globālie tirgus indeksi", name: "S&P 500 ilgtermiņa vidējais", assumption_return: 10.0, benchmark: true },
  { category: "Globālie tirgus indeksi", name: "MSCI World ilgtermiņa vidējais", assumption_return: 8.6, benchmark: true },
  { category: "Globālie tirgus indeksi", name: "NASDAQ-100 ilgtermiņa vidējais", assumption_return: 13.5, benchmark: true },
  { category: "Globālie tirgus indeksi", name: "Stoxx Europe 600 ilgtermiņa vidējais", assumption_return: 7.2, benchmark: true },

  // Passive / index-tracking plans
  { category: "Pasīvie / indeksu plāni", name: "SEB indeksu plāns 15-54", return_3y: 14.63, return_5y: 11.49, fee_total: 0.30 },
  { category: "Pasīvie / indeksu plāni", name: "INDEXO plāns Jauda 16-55", return_3y: 13.71, return_5y: 11.15, fee_total: 0.39 },
  { category: "Pasīvie / indeksu plāni", name: "INDEXO Izaugsme 16-55", return_3y: 12.42, return_5y: 9.82, fee_total: 0.46 },

  // Actively managed aggressive plans
  { category: "Aktīvie plāni", name: "SEB izaugsmes plāns 15-54", return_3y: 12.99, return_5y: 10.05, fee_total: 0.38 },
  { category: "Aktīvie plāni", name: "INVL MAKSIMĀLAIS 16+", return_3y: 12.08, return_5y: 9.34, fee_total: 0.74 },
  { category: "Aktīvie plāni", name: "CBL Aktīvais plāns", return_3y: 10.87, return_5y: 8.74, fee_total: 0.79 },
  { category: "Aktīvie plāni", name: "Luminor Aktīvais plāns", return_3y: 10.14, return_5y: 8.02, fee_total: 0.72 },

  // Lifecycle plans
  { category: "Dzīves cikla plāni", name: "Swedbank dzīves cikla plāns 1990+", return_3y: 11.61, return_5y: 9.19, fee_total: 0.37 },
  { category: "Dzīves cikla plāni", name: "Swedbank dzīves cikla plāns 1980+", return_3y: 11.42, return_5y: 9.09, fee_total: 0.37 },
  { category: "Dzīves cikla plāni", name: "Swedbank dzīves cikla plāns 1970+", return_3y: 10.88, return_5y: 8.61, fee_total: 0.37 },
  { category: "Dzīves cikla plāni", name: "SEB dzīves cikla plāns", return_3y: 10.77, return_5y: 8.54, fee_total: 0.63 },

  // Conservative / classic low-risk plans
  { category: "Klasiskie / konservatīvie", name: "Swedbank Stabilitāte", return_3y: 2.91, return_5y: 1.87, fee_total: 0.58 },
  { category: "Klasiskie / konservatīvie", name: "SEB konservatīvais plāns", return_3y: 2.74, return_5y: 1.65, fee_total: 0.32 },
  { category: "Klasiskie / konservatīvie", name: "Luminor Konservatīvais plāns", return_3y: 2.43, return_5y: 1.54, fee_total: 0.67 },
  { category: "Klasiskie / konservatīvie", name: "CBL Konservatīvais plāns", return_3y: 2.18, return_5y: 1.42, fee_total: 0.73 },

  // Balanced plans
  { category: "Sabalansētie plāni", name: "SEB Sabalansētais plāns", return_3y: 6.81, return_5y: 4.92, fee_total: 0.40 },
  { category: "Sabalansētie plāni", name: "Swedbank Sabalansētais plāns", return_3y: 6.54, return_5y: 4.61, fee_total: 0.39 },
  { category: "Sabalansētie plāni", name: "Luminor Sabalansētais plāns", return_3y: 6.12, return_5y: 4.22 },

  // ESG / sustainability-focused balanced plans
  { category: "Ilgtspējas / sabalansētie", name: "C Ilgtspējas plāns 15-50", return_3y: 8.91, return_5y: 6.24 },
  { category: "Ilgtspējas / sabalansētie", name: "Luminor Ilgtspējīgais plāns", return_3y: 8.33, return_5y: 6.01 },
];

// Find a plan by name, falling back to the first (custom) plan
export function getPlanByName(name) {
  return PLANS.find((p) => p.name === name) ?? PLANS[0];
}

// Latvian CPI annual inflation by calendar year (fraction, e.g. 0.0139 = 1.39 %)
export const HISTORICAL_INFLATION = {
  2002: 0.0139, 2003: 0.0361, 2004: 0.0733, 2005: 0.0696,
  2006: 0.0684, 2007: 0.1406, 2008: 0.1054, 2009: -0.0117,
  2010: 0.0254, 2011: 0.0403, 2012: 0.0160, 2013: -0.0042,
  2014: 0.0020, 2015: 0.0034, 2016: 0.0218, 2017: 0.0215,
  2018: 0.0255, 2019: 0.0226, 2020: -0.0050, 2021: 0.0792,
  2022: 0.2083, 2023: 0.0063, 2024: 0.0326, 2025: 0.0349,
};

// G coefficient (years) by retirement age — Latvia 2025, Cabinet Reg. Nr. 1445
// Monthly pension = capital / (G × 12); mirrors data.py G_TABLE
export const G_BY_AGE = {
  60: 22.0, 61: 21.2, 62: 20.4, 63: 19.5,
  64: 17.96, 65: 17.24, 66: 16.9, 67: 16.51,
  68: 16.1, 69: 15.7, 70: 15.3,
};

// Return G (years) clamped to the known table range 60–70
export function getGCoefficient(retirementAge) {
  const age = Math.max(60, Math.min(70, Math.round(Number(retirementAge))));
  return G_BY_AGE[age];
}

// Historical P2L contribution rates (% of gross) by calendar year
export function historicalP2lRate(year) {
  if (year <= 2006) return 0.02;   // 2001–2006: 2 %
  if (year === 2007) return 0.04;  // 2007: 4 %
  if (year === 2008) return 0.08;  // 2008: 8 %
  if (year <= 2012) return 0.02;   // 2009–2012: 2 %
  if (year <= 2014) return 0.04;   // 2013–2014: 4 %
  if (year === 2015) return 0.05;  // 2015: 5 %
  return 0.06;                     // 2016–present: 6 %
}

// 3rd-pillar IIN tax relief constants — mirrors data.py P3_* constants
export const P3_CONSTANTS = {
  TAX_DEDUCTION_CAP:  4_000,   // max annual contribution qualifying for refund
  TAX_DEDUCTION_RATE: 0.10,    // max 10% of annual gross qualifies
  IIN_RATE:           0.255,   // income-tax rate for refund calculation
  PAYOUT_GAINS_TAX:   0.255,   // tax on gains at payout
  MIN_PAYOUT_AGE:     55,      // earliest unrestricted withdrawal age
};

// 3rd-pillar open pension fund dataset — mirrors data.py P3_PLANS
// Update return_3y, return_5y, fee_total here AND in data.py when refreshing.
export const P3_PLANS = [
  { provider: "Swedbank", name: "Swedbank Dinamika 18-49",   return_3y: 14.51, return_5y: 9.20, fee_total: 0.65 },
  { provider: "Swedbank", name: "Swedbank Stabilitāte 50+",  return_3y:  5.80, return_5y: 3.90, fee_total: 0.55 },
  { provider: "SEB",      name: "SEB Aktīvais plāns",        return_3y: 11.66, return_5y: 8.48, fee_total: 0.95 },
  { provider: "SEB",      name: "SEB Sabalansētais plāns",   return_3y:  7.42, return_5y: 5.55, fee_total: 0.75 },
  { provider: "INDEXO",   name: "INDEXO 3. pīlārs",          return_3y: 10.50, return_5y: 8.20, fee_total: 0.40 },
  { provider: "CBL",      name: "CBL Aktīvais",              return_3y:  9.10, return_5y: 6.80, fee_total: 0.80 },
  { provider: "Luminor",  name: "Luminor Aktīvais",          return_3y:  8.20, return_5y: 6.10, fee_total: 0.85 },
  { provider: "INVL",     name: "INVL Aktīvais",             return_3y:  8.60, return_5y: 6.50, fee_total: 0.90 },
];

export function getP3PlanByName(name) {
  return P3_PLANS.find(p => p.name === name) ?? P3_PLANS[0];
}

// Historical Dinamika 18-49 NAV prices Feb 2019–May 2026 (source: Swedbank CSV)
const _DINAMIKA_PRICES = [
  1.62790, 1.63010, 1.69840, 1.66600, 1.66830, 1.72710, 1.66160,
  1.73010, 1.71720, 1.82040, 1.82280, 1.88360, 1.92540, 1.58040,
  1.59900, 1.66570, 1.76190, 1.76170, 1.77210, 1.80060, 1.84390,
  1.91570, 1.94100, 2.02870, 2.08220, 2.06740, 2.15920, 2.17650,
  2.19170, 2.27260, 2.32750, 2.35420, 2.31740, 2.45770, 2.47060,
  2.45000, 2.37830, 2.24510, 2.38520, 2.18160, 2.22300, 2.22210,
  2.31280, 2.28020, 2.12280, 2.16720, 2.21130, 2.19460, 2.28260,
  2.24640, 2.21980, 2.24310, 2.33210, 2.32140, 2.34920, 2.37470,
  2.31260, 2.31570, 2.43730, 2.48130, 2.59490, 2.65100, 2.66190,
  2.69690, 2.74360, 2.80110, 2.67140, 2.73830, 2.86590, 2.94240,
  3.01930, 2.94870, 3.04980, 2.80060, 2.52960, 2.74150, 2.85590,
  2.87310, 2.92760, 2.98120, 3.04250, 3.12500, 3.14910, 3.23930,
  3.22540, 3.18870, 3.20380, 3.39100,
];

// 87 monthly returns — mirrors data.py DINAMIKA_MONTHLY_RETURNS
export const DINAMIKA_MONTHLY_RETURNS = _DINAMIKA_PRICES.slice(1).map(
  (p, i) => p / _DINAMIKA_PRICES[i] - 1
);

// P3 cost basis — mirrors data.py P3_COST_BASIS
export const P3_COST_BASIS = 2_983.17;
