"""PL-01 entry: load prices."""
from quant.data.steps import apply_universe, read_raw


def run_load_prices(cfg):
    rows = read_raw(cfg.path, cfg.start, cfg.end)
    return apply_universe(rows, cfg.start, cfg.end)
