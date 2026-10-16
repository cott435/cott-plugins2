"""TFT target construction: forward log returns over a horizon, for a forecasting model."""
import numpy as np
import pandas as pd


def forward_returns(prices: pd.DataFrame, horizon: int = 5) -> pd.DataFrame:
    """Log return from t to t + horizon, aligned at t (the last `horizon` rows are NaN)."""
    return np.log(prices.shift(-horizon) / prices)
