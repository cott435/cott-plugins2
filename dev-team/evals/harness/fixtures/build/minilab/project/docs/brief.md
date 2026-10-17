# Minilab — Brief

**Status:** Accepted · **Last updated:** 2026-10-17

## Problem
I hold a handful of stocks and want one honest number per holding for how risky it has been: how much it swings in a year, and how far it fell from its high.

## Users
Me, the only user.

## Goals
1. Clean daily prices from the CSV exports I already have.
2. Each holding's yearly volatility, the way a year of my statements adds up, and its worst drawdown.
3. A report file I can diff from one month to the next.

## Constraints
- Python on a laptop, standard library only; the inputs are small CSV files.

## Not doing
- Live data, intraday prices, portfolio optimisation.
