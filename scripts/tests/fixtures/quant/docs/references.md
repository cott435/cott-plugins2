# Quant Lab — References

**Status:** Approved · **Last updated:** 2026-10-16

### RF-01: Market decomposition transforms
**File:** `references/market_decomposition.py` · **Hash:** fe5ddc3f · **Kind:** code · **Milestones:** M1
- **Purpose:** removes the market mode and the top-k factors from a returns panel by PCA; returns residuals and loadings
- **Key parts:** `demean_returns`, `pca_factors(returns, k)`, `residualize(returns, factors)`, `MarketRemover`
- **In → Out:** T×N returns DataFrame → residual returns (T×N), loadings (N×k), explained variance
- **Use for:** PL-02 `pca` step design; the planted-factor known-answer case (TC-03)
- **Caveats:** fits PCA on the whole sample (look-ahead); the project must fit per window

### RF-02: TFT target construction
**File:** `references/tft_targets.py` · **Hash:** d6ef7c17 · **Kind:** code · **Milestones:** —
- **Purpose:** forward log returns over a horizon, the target for a forecasting model
- **Key parts:** `forward_returns(prices, horizon)`
- **In → Out:** T×N prices → T×N forward log returns (last `horizon` rows NaN)
- **Use for:** a later forecasting stage
