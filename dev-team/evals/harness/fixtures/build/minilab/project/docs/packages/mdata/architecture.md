# mdata — Architecture

**Package:** mdata · **Status:** Approved · **Last updated:** 2026-10-17 · **Root:** [../../architecture.md](../../architecture.md)

## Overview
Reads a prices CSV, drops what can't be used, and puts every ticker on one calendar.

## Components
| Component | Responsibility | Covers | Depends on |
|---|---|---|---|
| `io` | Read the CSV | DATA-01 | — |
| `validate` | Drop unusable rows, resolve duplicates | DATA-02 | — |
| `calendar` | One calendar, forward fill, gap limit | DATA-03, DATA-04 | — |

## Interfaces
See [contract.md](contract.md).

## Project layout
```
packages/mdata/src/mdata/
  __init__.py  types.py  io.py  validate.py  calendar.py  pipeline.py
```
