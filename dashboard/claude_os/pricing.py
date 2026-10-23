# shortcut: static prices from Anthropic's list as of 2026-10-06, update when they change.
# $ per 1M tokens: input, output, cache read. A 5-minute cache write costs 1.25x input, a 1-hour one 2x.
PRICES = {
    "claude-fable-5-1": (10.00, 50.00, 0.25),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
}
WRITE_5M, WRITE_1H = 1.25, 2.0


def rates(model):
    """The price row for a model id; '[1m]' and other suffixes after the id are ignored."""
    for mid, row in PRICES.items():
        if model and model.startswith(mid):
            return row
    return None
