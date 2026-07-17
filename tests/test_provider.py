"""Tests for the market-data provider contract."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from python_exchange_integration_runtime import (
    ExchangeEndpoint,
    ExchangeRequest,
    ExchangeResponse,
)

from python_market_data_downloader import MarketDataProvider
from python_market_data_downloader.errors import ProviderConfigurationError
from python_market_data_downloader.models import HistoricalCandleRequest
from python_market_data_downloader.provider import _ProviderCandleRecord, _ProviderPage


class _DummyProvider(MarketDataProvider):
    """Concrete provider used to verify contract behavior."""

    def build_exchange_request(
        self,
        request: HistoricalCandleRequest,
        *,
        start_time_ms: int,
        end_time_ms: int,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> ExchangeRequest:
        del start_time_ms
        del end_time_ms
        del page_size
        del page_token
        return ExchangeRequest(
            endpoint=ExchangeEndpoint(
                name="public_candles",
                method="GET",
                path="/v1/candles",
            ),
            query_params={
                "symbol": request.symbol,
                "timeframe": request.timeframe,
            },
        )

    def parse_page(
        self,
        request: HistoricalCandleRequest,
        response: ExchangeResponse,
    ) -> _ProviderPage:
        del request
        del response
        return _ProviderPage(
            records=(
                _ProviderCandleRecord(
                    open_time_ms=0,
                    open_price="100.0",
                    high_price="101.0",
                    low_price="99.0",
                    close_price="100.5",
                    volume="42.0",
                ),
            ),
            is_complete=True,
        )


def test_market_data_provider_is_exported_from_package_root() -> None:
    """Verify the provider contract is part of the approved public API."""
    assert MarketDataProvider is not None


def test_market_data_provider_normalizes_provider_id() -> None:
    """Verify provider identifiers are normalized and stored immutably."""
    provider = _DummyProvider(provider_id=" bybit_spot ")

    assert provider.provider_id == "bybit_spot"

    with pytest.raises(
        ProviderConfigurationError,
        match="Provider id must be non-empty.",
    ):
        _DummyProvider(provider_id="   ")


def test_provider_candle_record_is_immutable() -> None:
    """Verify provider-native records are immutable."""
    record = _ProviderCandleRecord(
        open_time_ms=0,
        open_price="100.0",
        high_price="101.0",
        low_price="99.0",
        close_price="100.5",
        volume="42.0",
    )

    with pytest.raises(FrozenInstanceError):
        record.open_price = "101.0"  # type: ignore[misc]


def test_provider_candle_record_validates_invariants() -> None:
    """Verify provider-native records enforce local invariants."""
    record = _ProviderCandleRecord(
        open_time_ms=0,
        open_price="100.0",
        high_price="101.0",
        low_price="99.0",
        close_price="100.5",
        volume="42.0",
    )

    assert record.volume == "42.0"

    with pytest.raises(
        ValueError,
        match=(
            "Provider candle record close_price must be within the inclusive "
            "low_price and high_price range."
        ),
    ):
        _ProviderCandleRecord(
            open_time_ms=0,
            open_price="100.0",
            high_price="101.0",
            low_price="99.0",
            close_price="120.0",
        )


def test_provider_page_is_immutable() -> None:
    """Verify provider pages are immutable."""
    page = _ProviderPage(
        records=(),
        next_page_token="cursor-1",
        is_complete=False,
    )

    with pytest.raises(FrozenInstanceError):
        page.is_complete = True  # type: ignore[misc]


def test_provider_page_validates_pagination_metadata() -> None:
    """Verify provider pages validate completion and token consistency."""
    page = _ProviderPage(
        records=(),
        next_page_token=" cursor-1 ",
        is_complete=False,
    )

    assert page.next_page_token == "cursor-1"

    with pytest.raises(
        ValueError,
        match=(
            "Provider page next_page_token must be omitted when is_complete "
            "is True."
        ),
    ):
        _ProviderPage(
            records=(),
            next_page_token="cursor-2",
            is_complete=True,
        )


def test_concrete_provider_implements_contract_methods() -> None:
    """Verify concrete providers can produce request and page artifacts."""
    provider = _DummyProvider(provider_id="bybit_spot")
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
    )
    exchange_request = provider.build_exchange_request(
        request,
        start_time_ms=0,
        end_time_ms=60_000,
    )
    exchange_response = ExchangeResponse(
        endpoint=exchange_request.endpoint,
        status_code=200,
        payload={},
    )
    page = provider.parse_page(request, exchange_response)

    assert exchange_request.query_params == {
        "symbol": "BTCUSDT",
        "timeframe": "1m",
    }
    assert page.is_complete is True
    assert len(page.records) == 1
