"""Market decomposition: remove the market mode and the top-k factors from a returns panel by PCA."""
import numpy as np
import pandas as pd


def demean_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """Subtract each column's mean."""
    return returns - returns.mean()


def pca_factors(returns: pd.DataFrame, k: int = 3) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Top-k principal components of the demeaned returns: (factors T×k, loadings N×k, explained variance)."""
    x = demean_returns(returns).to_numpy()
    u, s, vt = np.linalg.svd(x, full_matrices=False)
    factors = pd.DataFrame(u[:, :k] * s[:k], index=returns.index)
    explained = (s ** 2 / (s ** 2).sum())[:k]
    return factors, vt[:k].T, explained


def residualize(returns: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    """Returns minus their least-squares projection on the factors."""
    beta, *_ = np.linalg.lstsq(factors.to_numpy(), returns.to_numpy(), rcond=None)
    return returns - factors.to_numpy() @ beta


class MarketRemover:
    """Fits PCA once on the whole sample, then residualizes any panel."""

    def __init__(self, k: int = 1):
        self.k = k

    def fit(self, returns: pd.DataFrame) -> "MarketRemover":
        """Fit the factors on the whole sample (look-ahead)."""
        self.factors_, self.loadings_, _ = pca_factors(returns, self.k)
        return self

    def transform(self, returns: pd.DataFrame) -> pd.DataFrame:
        return residualize(returns, self.factors_)
