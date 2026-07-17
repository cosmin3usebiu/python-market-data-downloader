"""Tests for immutable public models and repository exceptions."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from python_market_data_downloader import (
    DownloadResult,
    HistoricalCandle,
    HistoricalCandleRequest,
)
from python_market_data_downloader.errors import (
    DownloadExecutionError,
    DownloadPlanningError,
    MarketDataDownloaderError,
    NormalizationError,
    ProviderConfigurationError,
)


def test_historical_candle_request_is_immutable() -> None:
    """Verify download request models are immutable."""
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
    )

    with pytest.raises(FrozenInstanceError):
        request.symbol = "ETHUSDT"  # type: ignore[misc]


def test_historical_candle_request_normalizes_and_validates() -> None:
    """Verify request models normalize identifiers and validate intervals."""
    request = HistoricalCandleRequest(
        symbol=" BTCUSDT ",
        timeframe=" 1m ",
        start_time_ms=1_000,
        end_time_ms=61_000,
        page_size=200,
        max_requests=10,
    )

    assert request.symbol == "BTCUSDT"
    assert request.timeframe == "1m"
    assert request.page_size == 200
    assert request.max_requests == 10

    with pytest.raises(
        ValueError,
        match=(
            "Historical candle request end_time_ms must be greater than "
            "start_time_ms."
        ),
    ):
        HistoricalCandleRequest(
            symbol="BTCUSDT",
            timeframe="1m",
            start_time_ms=10,
            end_time_ms=10,
        )

    with pytest.raises(TypeError, match="page_size must be an integer."):
        HistoricalCandleRequest(
            symbol="BTCUSDT",
            timeframe="1m",
            start_time_ms=0,
            end_time_ms=1,
            page_size="100",  # type: ignore[arg-type]
        )


def test_historical_candle_is_immutable() -> None:
    """Verify canonical candle models are immutable."""
    candle = HistoricalCandle(
        provider_id="bybit",
        symbol="BTCUSDT",
        timeframe="1m",
        open_time_ms=0,
        open_price="100.0",
        high_price="101.0",
        low_price="99.0",
        close_price="100.5",
        volume="42.0",
    )

    with pytest.raises(FrozenInstanceError):
        candle.close_price = "101.0"  # type: ignore[misc]


def test_historical_candle_validates_invariants() -> None:
    """Verify candle invariants are enforced locally."""
    candle = HistoricalCandle(
        provider_id=" bybit ",
        symbol=" BTCUSDT ",
        timeframe=" 1m ",
        open_time_ms=0,
        open_price="100.0",
        high_price="110.0",
        low_price="90.0",
        close_price="95.0",
        volume="15.25",
    )

    assert candle.provider_id == "bybit"
    assert candle.symbol == "BTCUSDT"
    assert candle.timeframe == "1m"
    assert candle.volume == "15.25"

    with pytest.raises(
        ValueError,
        match=(
            "Historical candle open_price must be within the inclusive "
            "low_price and high_price range."
        ),
    ):
        HistoricalCandle(
            provider_id="bybit",
            symbol="BTCUSDT",
            timeframe="1m",
            open_time_ms=0,
            open_price="120.0",
            high_price="110.0",
            low_price="90.0",
            close_price="100.0",
        )

    with pytest.raises(ValueError, match="volume must be non-negative."):
        HistoricalCandle(
            provider_id="bybit",
            symbol="BTCUSDT",
            timeframe="1m",
            open_time_ms=0,
            open_price="100.0",
            high_price="110.0",
            low_price="90.0",
            close_price="100.0",
            volume="-1",
        )


def test_download_result_is_immutable() -> None:
    """Verify download result models are immutable."""
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=120_000,
    )
    candle = HistoricalCandle(
        provider_id="bybit",
        symbol="BTCUSDT",
        timeframe="1m",
        open_time_ms=0,
        open_price="100.0",
        high_price="101.0",
        low_price="99.0",
        close_price="100.5",
        volume="42.0",
    )
    result = DownloadResult(
        request=request,
        provider_id="bybit",
        candles=(candle,),
        returned_start_time_ms=0,
        returned_end_time_ms=0,
        total_pages=1,
        total_requests=1,
        execution_duration_seconds=0.5,
    )

    with pytest.raises(FrozenInstanceError):
        result.total_pages = 2  # type: ignore[misc]


def test_download_result_validates_ordering_and_metadata() -> None:
    """Verify result models validate canonical ordering and metadata."""
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=180_000,
    )
    candle_one = HistoricalCandle(
        provider_id="bybit",
        symbol="BTCUSDT",
        timeframe="1m",
        open_time_ms=0,
        open_price="100.0",
        high_price="101.0",
        low_price="99.0",
        close_price="100.5",
        volume="42.0",
    )
    candle_two = HistoricalCandle(
        provider_id="bybit",
        symbol="BTCUSDT",
        timeframe="1m",
        open_time_ms=60_000,
        open_price="100.5",
        high_price="102.0",
        low_price="100.0",
        close_price="101.0",
        volume="30.0",
    )

    result = DownloadResult(
        request=request,
        provider_id="bybit",
        candles=(candle_one, candle_two),
        returned_start_time_ms=0,
        returned_end_time_ms=60_000,
        total_pages=2,
        total_requests=2,
    )

    assert result.candles[0].open_time_ms == 0
    assert result.candles[1].open_time_ms == 60_000
    assert result.total_pages == 2
    assert result.total_requests == 2

    with pytest.raises(
        ValueError,
        match="Download result candles must be ordered from oldest to newest.",
    ):
        DownloadResult(
            request=request,
            provider_id="bybit",
            candles=(candle_two, candle_one),
            returned_start_time_ms=60_000,
            returned_end_time_ms=0,
        )

    with pytest.raises(
        ValueError,
        match=(
            "Download result returned interval metadata must be omitted when "
            "candles are empty."
        ),
    ):
        DownloadResult(
            request=request,
            provider_id="bybit",
            candles=(),
            returned_start_time_ms=0,
            returned_end_time_ms=0,
        )

    with pytest.raises(
        ValueError,
        match="Download result candles must all use the result provider_id.",
    ):
        DownloadResult(
            request=request,
            provider_id="binance",
            candles=(candle_one,),
            returned_start_time_ms=0,
            returned_end_time_ms=0,
        )


def test_repository_exception_hierarchy_uses_one_root_type() -> None:
    """Verify repository-specific exceptions derive from one stable root type."""
    exceptions = (
        ProviderConfigurationError("provider error"),
        DownloadPlanningError("planning error"),
        DownloadExecutionError("execution error"),
        NormalizationError("normalization error"),
    )

    for exception in exceptions:
        assert isinstance(exception, MarketDataDownloaderError)
