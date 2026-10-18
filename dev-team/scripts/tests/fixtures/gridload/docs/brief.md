# GridLoad — Brief

**Status:** Accepted · **Last updated:** 2026-10-17

## Problem
The utility plans tomorrow's reserves from last year's same-day load. I want day-ahead demand forecasts per region that beat that, and to learn forecasting by building them.

## Users
Me, the only user: one analyst on the planning team.

## Goals
1. A clean hourly load history per region, decommissioned meters included.
2. Seasonal profiles that explain most of the daily and weekly swing.
3. Day-ahead forecasts that beat seasonal-naive on held-out weeks.

## Constraints
- Python on a laptop; the utility's own meter export plus a free weather API.

## Not doing
- Real-time dispatch, pricing, anything customer-facing.
