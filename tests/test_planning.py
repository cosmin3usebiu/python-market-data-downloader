"""Tests for deterministic download planning."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest
from python_exchange_integration_runtime import (
    ExchangeEndpoint,
    ExchangeRequest,
    ExchangeResponse,
)

from python_market_data_downloader import MarketDataProvider
from python_market_data_downloader.errors import DownloadPlanningError
from python_market_data_downloader.models import HistoricalCandleRequest
from python_market_data_downloader.planning import (
    _build_download_plan,
    _get_next_window,
    _is_plan_complete,
)
from python_market_data_downloader.provider import _ProviderPage


class _DummyProvider(MarketDataProvider):
    """Concrete provider used to verify planning behavior."""

    def build_exchange_request(
        self,
        request: HistoricalCandleRequest,
        *,
        start_time_ms: int,
        end_time_ms: int,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> ExchangeRequest:
        del request
        del start_time_ms
        del end_time_ms
        del page_size
        del page_token
        return ExchangeRequest(
            endpoint=ExchangeEndpoint(
                name="public_candles",
                method="GET",
                path="/v1/candles",
            )
        )

    def parse_page(
        self,
        request: HistoricalCandleRequest,
        response: ExchangeResponse,
    ) -> _ProviderPage:
        del request
        del response
        return _ProviderPage(records=(), is_complete=True)


def test_download_window_is_immutable() -> None:
    """Verify internal planning windows are immutable."""
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
        page_size=1,
    )
    provider = _DummyProvider(provider_id="bybit_spot")
    plan = _build_download_plan(request, provider)
    window = plan.windows[0]

    with pytest.raises(FrozenInstanceError):
        window.end_time_ms = 120_000  # type: ignore[misc]


def test_build_download_plan_uses_single_window_without_page_size() -> None:
    """Verify planning defaults to one full-interval window when page_size is unset."""
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=300_000,
    )
    provider = _DummyProvider(provider_id="bybit_spot")

    plan = _build_download_plan(request, provider)

    assert plan.provider_id == "bybit_spot"
    assert plan.timeframe_ms == 60_000
    assert len(plan.windows) == 1
    assert plan.windows[0].start_time_ms == 0
    assert plan.windows[0].end_time_ms == 300_000
    assert plan.windows[0].page_size is None


def test_build_download_plan_slices_request_into_deterministic_windows() -> None:
    """Verify planning slices requests by timeframe and page_size without overlap."""
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=300_000,
        page_size=2,
    )
    provider = _DummyProvider(provider_id="bybit_spot")

    plan = _build_download_plan(request, provider)

    assert len(plan.windows) == 3
    assert [(window.start_time_ms, window.end_time_ms) for window in plan.windows] == [
        (0, 120_000),
        (120_000, 240_000),
        (240_000, 300_000),
    ]


def test_build_download_plan_is_deterministic() -> None:
    """Verify identical requests produce identical plans."""
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="5m",
        start_time_ms=0,
        end_time_ms=3_600_000,
        page_size=3,
    )
    provider = _DummyProvider(provider_id="bybit_spot")

    left_plan = _build_download_plan(request, provider)
    right_plan = _build_download_plan(request, provider)

    assert left_plan == right_plan


def test_build_download_plan_rejects_unsupported_timeframes() -> None:
    """Verify unsupported timeframes fail with repository-native planning errors."""
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1x",
        start_time_ms=0,
        end_time_ms=60_000,
    )
    provider = _DummyProvider(provider_id="bybit_spot")

    with pytest.raises(
        DownloadPlanningError,
        match="Download planning does not support timeframe unit 'x'.",
    ):
        _build_download_plan(request, provider)


def test_build_download_plan_rejects_unsatisfied_max_requests() -> None:
    """Verify unsatisfiable max_requests constraints fail fast."""
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=300_000,
        page_size=1,
        max_requests=4,
    )
    provider = _DummyProvider(provider_id="bybit_spot")

    with pytest.raises(
        DownloadPlanningError,
        match=(
            "Download planning requires more windows than request max_requests "
            "allows."
        ),
    ):
        _build_download_plan(request, provider)


def test_get_next_window_uses_completed_window_count() -> None:
    """Verify completion state maps deterministically to the next planned window."""
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=180_000,
        page_size=1,
    )
    provider = _DummyProvider(provider_id="bybit_spot")
    plan = _build_download_plan(request, provider)

    first_window = _get_next_window(plan, completed_windows=0)
    second_window = _get_next_window(plan, completed_windows=1)

    assert first_window.index == 0
    assert second_window.index == 1


def test_is_plan_complete_detects_completion() -> None:
    """Verify plan completion detection is deterministic and side-effect free."""
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=120_000,
        page_size=1,
    )
    provider = _DummyProvider(provider_id="bybit_spot")
    plan = _build_download_plan(request, provider)

    assert _is_plan_complete(plan, completed_windows=0) is False
    assert _is_plan_complete(plan, completed_windows=2) is True

    with pytest.raises(
        DownloadPlanningError,
        match="Download plan is already complete.",
    ):
        _get_next_window(plan, completed_windows=2)
