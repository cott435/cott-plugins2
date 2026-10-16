"""Market-mode removal for a daily returns panel by PCA.

Written while working through the "remove the market, then look at what's left" exercise. Takes a T x N
panel of simple daily returns (dates x tickers), finds the dominant principal components of the
correlation structure and regresses them out, leaving residual (idiosyncratic) returns.

The decomposition is fit on the whole panel passed in: the eigenvectors, the standardisation and the
loadings all use every row, including the last one.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def demean_returns(returns: pd.DataFrame, min_obs: int = 60) -> pd.DataFrame:
    """Drop thin columns, fill the remaining gaps with 0 and subtract each column's mean.

    Columns with fewer than ``min_obs`` non-missing rows are dropped. Missing values left after that are
    treated as a zero return (no trade that day).
    """
    keep = returns.columns[returns.notna().sum() >= min_obs]
    r = returns[keep].fillna(0.0)
    return r - r.mean(axis=0)


def standardise(returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Scale each column to unit variance; returns the scaled panel and the per-column std used."""
    sd = returns.std(axis=0, ddof=1).replace(0.0, np.nan)
    return returns.divide(sd, axis=1).fillna(0.0), sd


def pca_factors(returns: pd.DataFrame, k: int = 1) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    """Top-k principal components of the standardised returns.

    Returns:
        factors: T x k factor return series (projections of each day onto the eigenvectors).
        loadings: N x k eigenvectors, sign-fixed so each column has a positive sum (the market mode then
            loads positively on almost every stock).
        explained: the fraction of total variance explained by each of the k components.
    """
    z, _ = standardise(demean_returns(returns))
    corr = np.corrcoef(z.to_numpy(), rowvar=False)
    evals, evecs = np.linalg.eigh(corr)
    order = np.argsort(evals)[::-1]
    evals, evecs = evals[order], evecs[:, order]
    vecs = evecs[:, :k]
    vecs = vecs * np.sign(vecs.sum(axis=0, keepdims=True))
    cols = [f"pc{i + 1}" for i in range(k)]
    loadings = pd.DataFrame(vecs, index=z.columns, columns=cols)
    factors = pd.DataFrame(z.to_numpy() @ vecs, index=z.index, columns=cols)
    explained = evals[:k] / evals.sum()
    return factors, loadings, explained


def residualize(returns: pd.DataFrame, factors: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Regress each column of ``returns`` on ``factors`` (OLS with intercept) and return the residuals.

    Returns:
        residuals: T x N residual returns, same index and columns as the demeaned input.
        betas: N x k factor exposures.
    """
    r = demean_returns(returns)
    f = factors.loc[r.index].to_numpy()
    x = np.column_stack([np.ones(len(f)), f])
    coef, *_ = np.linalg.lstsq(x, r.to_numpy(), rcond=None)
    fitted = x @ coef
    residuals = pd.DataFrame(r.to_numpy() - fitted, index=r.index, columns=r.columns)
    betas = pd.DataFrame(coef[1:].T, index=r.columns, columns=factors.columns)
    return residuals, betas


def remove_market(returns: pd.DataFrame, k: int = 1) -> dict[str, object]:
    """Convenience wrapper: PCA on the panel, then residualize on the top-k components.

    Returns a dict with ``residuals`` (T x N), ``loadings`` (N x k), ``betas`` (N x k), ``factors``
    (T x k) and ``explained`` (length k).
    """
    factors, loadings, explained = pca_factors(returns, k)
    residuals, betas = residualize(returns, factors)
    return {"residuals": residuals, "loadings": loadings, "betas": betas, "factors": factors,
            "explained": explained}


def residual_correlation_check(residuals: pd.DataFrame) -> float:
    """Mean absolute off-diagonal correlation of the residuals; should drop sharply versus raw returns."""
    c = np.corrcoef(residuals.to_numpy(), rowvar=False)
    n = c.shape[0]
    off = c[~np.eye(n, dtype=bool)]
    return float(np.nanmean(np.abs(off)))


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    days, stocks = 750, 40
    market = rng.normal(0.0004, 0.01, days)
    beta = rng.uniform(0.6, 1.4, stocks)
    idio = rng.normal(0.0, 0.015, (days, stocks))
    panel = pd.DataFrame(market[:, None] * beta + idio,
                         index=pd.bdate_range("2020-01-01", periods=days),
                         columns=[f"S{i:02d}" for i in range(stocks)])
    out = remove_market(panel, k=1)
    print("explained:", np.round(out["explained"], 3))
    print("raw |corr|:", round(residual_correlation_check(demean_returns(panel)), 3))
    print("resid |corr|:", round(residual_correlation_check(out["residuals"]), 3))
