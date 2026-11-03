from decimal import Decimal

import httpx
import pytest

from wazn_screen.sources import (
    EgxBff,
    Funds,
    FxRates,
    HttpClient,
    Metals,
    Mubasher,
    ShariaRatings,
)
from wazn_screen.sources.egx_bff import _extract_symbols


def _client(handler):
    return HttpClient(transport=httpx.MockTransport(handler))


# EGX BFF
def test_egx_bff_shariah_symbols_dict_shape():
    def handler(req):
        assert "index-constituents" in str(req.url)
        return httpx.Response(
            200,
            json={"data": {"constituents": [{"symbol": "etel"}, {"symbol": " ADIB "}]}},
        )

    bff = EgxBff(http=_client(handler))
    assert bff.shariah_symbols() == ["ETEL", "ADIB"]


def test_egx_bff_shariah_symbols_list_shape():
    def handler(req):
        return httpx.Response(200, json={"data": ["etel", "ADIB", "adib"]})

    bff = EgxBff(http=_client(handler))
    assert bff.shariah_symbols() == ["ETEL", "ADIB"]


def test_egx_bff_missing_data_raises():
    def handler(req):
        return httpx.Response(200, json={"error": "nope"})

    bff = EgxBff(http=_client(handler))
    from wazn_screen.sources.http import HttpError

    with pytest.raises(HttpError):
        bff.shariah_symbols()


def test_egx_bff_market_status_passthrough():
    def handler(req):
        assert str(req.url).endswith("/market-status")
        return httpx.Response(200, json={"data": {"open": True}})

    bff = EgxBff(http=_client(handler))
    assert bff.market_status() == {"open": True}


def test_extract_symbols_dedupes_and_normalises():
    assert _extract_symbols([{"symbol": "a"}, {"ticker": "B"}, "a"]) == ["A", "B"]
    assert _extract_symbols({"symbols": [" x ", "", None]}) == ["X"]


# Mubasher
def test_mubasher_prices():
    def handler(req):
        return httpx.Response(200, json={"prices": [{"s": "ETEL", "p": 30}, "junk"]})

    m = Mubasher(http=_client(handler))
    assert m.prices() == [{"s": "ETEL", "p": 30}]


def test_mubasher_companies():
    def handler(req):
        return httpx.Response(200, json={"rows": [{"name": "ACME"}]})

    assert Mubasher(http=_client(handler)).companies() == [{"name": "ACME"}]


# Ratings
def test_ratings_consensus_mixed():
    def handler(req):
        return httpx.Response(
            200,
            json={
                "ETEL": {
                    "halal_bourse": "halal",
                    "musaffa": "haram",
                    "kashif": "halal",
                    "halal_invest": {"verdict": "doubtful"},
                    "faisal_bank": None,
                    "osoul": "yes",
                    "thndr": "no",
                    "mohamed_ramadan_sharia": "حلال",
                }
            },
        )

    r = ShariaRatings(http=_client(handler)).consensus("etel")
    assert r is not None
    assert r.symbol == "ETEL"
    assert r.halal == 4  # halal_bourse, kashif, osoul("yes"), ar-halal
    assert r.haram == 2  # musaffa, thndr("no")
    assert r.doubtful == 1
    assert r.unknown == 1
    assert r.majority == "doubtful"  # 4/8 is not strict majority
    assert r.any_haram is True


def test_ratings_missing_symbol():
    def handler(req):
        return httpx.Response(200, json={})

    assert ShariaRatings(http=_client(handler)).consensus("ETEL") is None


def test_ratings_list_shape():
    def handler(req):
        return httpx.Response(
            200,
            json=[
                {"symbol": "etel", "halal_bourse": "halal", "musaffa": "halal"},
                "junk",
            ],
        )

    rows = ShariaRatings(http=_client(handler)).consensus_all()
    assert "ETEL" in rows
    assert rows["ETEL"].halal == 2


# FX
def test_fx_rates():
    def handler(req):
        return httpx.Response(200, json={"rates": {"USD": 0.021, "EUR": 0.019}})

    fx = FxRates(http=_client(handler))
    r = fx.latest()
    assert r["USD"] == Decimal("0.021")
    assert fx.rate("eur") == Decimal("0.019")


# Metals
def test_metals_rates_per_gram():
    def handler(req):
        return httpx.Response(
            200,
            json={
                "data": {
                    "market_data": {
                        "rates_per_gram": {"gold_24k": 4500, "silver": 55.5}
                    }
                }
            },
        )

    m = Metals(http=_client(handler)).rates_per_gram()
    assert m["gold_24k"] == Decimal("4500")
    assert m["silver"] == Decimal("55.5")


# Funds
def test_funds_islamic_filter():
    def handler(req):
        return httpx.Response(
            200,
            json={
                "result": {
                    "data": {
                        "json": {
                            "funds": [
                                {"name": "A", "isIslamic": True},
                                {"name": "B", "isIslamic": False},
                                {"name": "C", "isIslamic": "yes"},
                            ]
                        }
                    }
                }
            },
        )

    f = Funds(http=_client(handler))
    assert [x["name"] for x in f.islamic()] == ["A", "C"]
