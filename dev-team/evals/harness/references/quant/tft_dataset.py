"""Dataset builder for a temporal-fusion-transformer style forecaster.

Turns a long panel (one row per ticker and date) into fixed-length training windows. Each window has an
encoder part (the lookback) and a decoder part (the forecast horizon), and the inputs are split the way
TFT expects them:

- static covariates: constant per ticker (sector, listing exchange, ...), categorical, encoded as ints
- known covariates: known in advance for every step, including the decoder steps (calendar features)
- observed covariates: only known up to the forecast origin (returns, volume, the engineered features)

Targets come from a separate frame (see tft_targets.py) joined on (ticker, date).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class WindowSpec:
    """Shape of one sample: ``lookback`` encoder steps followed by ``horizon`` decoder steps."""
    lookback: int = 63
    horizon: int = 5
    stride: int = 1
    static_cols: list[str] = field(default_factory=lambda: ["sector"])
    known_cols: list[str] = field(default_factory=lambda: ["dow", "month", "days_to_month_end"])
    observed_cols: list[str] = field(default_factory=lambda: ["log_ret", "log_volume", "range_pct"])
    target_cols: list[str] = field(default_factory=lambda: ["fwd_ret_1d"])


def add_calendar_features(panel: pd.DataFrame) -> pd.DataFrame:
    """Known-in-advance covariates derived from the date only."""
    p = panel.copy()
    d = pd.to_datetime(p["date"])
    p["dow"] = d.dt.dayofweek
    p["month"] = d.dt.month - 1
    month_end = d + pd.offsets.BMonthEnd(0)
    p["days_to_month_end"] = np.busday_count(d.values.astype("datetime64[D]"),
                                             month_end.values.astype("datetime64[D]"))
    return p


def encode_static(panel: pd.DataFrame, cols: list[str]) -> tuple[pd.DataFrame, dict[str, dict[str, int]]]:
    """Map each static categorical column to integer codes; returns the panel and the vocabularies."""
    p = panel.copy()
    vocab = {}
    for c in cols:
        cats = sorted(p[c].astype(str).unique())
        vocab[c] = {v: i for i, v in enumerate(cats)}
        p[c] = p[c].astype(str).map(vocab[c]).astype(np.int64)
    return p, vocab


def normalise_observed(panel: pd.DataFrame, cols: list[str], window: int = 252) -> pd.DataFrame:
    """Per-ticker z-score of observed covariates using a trailing window (no future rows)."""
    p = panel.sort_values(["ticker", "date"]).copy()
    g = p.groupby("ticker")[cols]
    mu = g.transform(lambda s: s.rolling(window, min_periods=20).mean())
    sd = g.transform(lambda s: s.rolling(window, min_periods=20).std())
    p[cols] = ((p[cols] - mu) / sd.replace(0.0, np.nan)).fillna(0.0)
    return p


def build_windows(panel: pd.DataFrame, targets: pd.DataFrame, spec: WindowSpec) -> dict[str, np.ndarray]:
    """Slice every ticker's history into windows.

    Returns arrays keyed by name, with S samples:
        static   (S, n_static)              int64
        known    (S, lookback + horizon, n_known)
        observed (S, lookback, n_observed)
        target   (S, horizon, n_target)
        origin   (S,) the forecast-origin date of each sample (last encoder step)
        ticker   (S,)
    """
    df = panel.merge(targets, on=["ticker", "date"], how="inner").sort_values(["ticker", "date"])
    span = spec.lookback + spec.horizon
    out = {k: [] for k in ("static", "known", "observed", "target", "origin", "ticker")}
    for tk, g in df.groupby("ticker", sort=True):
        if len(g) < span:
            continue
        st = g[spec.static_cols].iloc[0].to_numpy(dtype=np.int64)
        kn = g[spec.known_cols].to_numpy(dtype=np.float32)
        ob = g[spec.observed_cols].to_numpy(dtype=np.float32)
        tg = g[spec.target_cols].to_numpy(dtype=np.float32)
        dates = g["date"].to_numpy()
        for start in range(0, len(g) - span + 1, spec.stride):
            enc_end = start + spec.lookback
            out["static"].append(st)
            out["known"].append(kn[start:start + span])
            out["observed"].append(ob[start:enc_end])
            out["target"].append(tg[enc_end - 1:enc_end - 1 + spec.horizon])
            out["origin"].append(dates[enc_end - 1])
            out["ticker"].append(tk)
    return {k: np.stack(v) if v else np.empty((0,)) for k, v in out.items()}


def split_by_origin(arrays: dict[str, np.ndarray], train_end: str, valid_end: str) -> dict[str, dict[str, np.ndarray]]:
    """Train / valid / test split on each sample's forecast-origin date."""
    origin = pd.to_datetime(arrays["origin"])
    masks = {"train": origin <= pd.Timestamp(train_end),
             "valid": (origin > pd.Timestamp(train_end)) & (origin <= pd.Timestamp(valid_end)),
             "test": origin > pd.Timestamp(valid_end)}
    return {name: {k: v[m] for k, v in arrays.items()} for name, m in masks.items()}
