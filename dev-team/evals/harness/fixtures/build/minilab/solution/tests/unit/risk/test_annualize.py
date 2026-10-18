import dataclasses

from risk.annualize import annualize
from risk.types import Returns, VolSeries


def test_keeps_shape_and_gaps(contract_sample):
    s = contract_sample("risk.VolSeries")
    r = s["returns"]
    v = VolSeries(
        returns=Returns(
            base_date=r["base_date"],
            dates=tuple(r["dates"]),
            tickers=tuple(r["tickers"]),
            values={t: tuple(x) for t, x in r["values"].items()},
        ),
        window=s["window"],
        annualized=False,
        values={t: tuple(x) for t, x in s["values"].items()},
    )
    got = annualize(dataclasses.replace(v))
    assert {t: [x is None for x in xs] for t, xs in got.values.items()} == {
        t: [x is None for x in xs] for t, xs in v.values.items()
    }
