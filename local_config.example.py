# Copy this file to local_config.py and fill in your own values.
# local_config.py is gitignored — it will never be committed.
#
# You only need this file for personalised Monte Carlo simulations using
# your own Dinamika 18-49 NAV history.
# All form values (balance, salary, birth year, etc.) are saved
# automatically in your browser's localStorage — they never leave your
# machine or touch the server.

# Historical Dinamika 18-49 NAV prices (monthly, from Swedbank CSV export).
# Must have at least 2 values. Leave as [] to use fixed fallback rates
# (10% / 7.5% / 3%) for the three scenario buttons.
_DINAMIKA_PRICES = []

# Your P3 cost basis accumulated BEFORE the simulation window (EUR).
# Set to 0.0 if all contributions happen within the simulation period.
P3_COST_BASIS = 0.0
