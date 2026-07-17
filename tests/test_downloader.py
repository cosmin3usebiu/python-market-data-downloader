"""Tests for downloader orchestration."""

from __future__ import annotations

import pytest
from python_exchange_integration_runtime import (
    ExchangeEndpoint,
    ExchangeRequest,
    ExchangeResponse,
    ExchangeRuntime,
)

from python_market_data_downloader import (
    DownloadResult,
    HistoricalCandleRequest,
    MarketDataDownloader,
    MarketDataProvider,
)
from python_market_data_downloader.errors import (
    DownloadExecutionError,
    DownloadPlanningError,
    NormalizationError,
    ProviderConfigurationError,
)
from python_market_data_downloader.provider import _ProviderCandleRecord, _ProviderPage


class _RecordingRuntime(ExchangeRuntime):
    """Exchange runtime double that records executed exchange requests."""

    def __init__(self, responses: tuple[ExchangeResponse, ...]) -> None:
        self.responses = list(responses)
        self.requests: list[ExchangeRequest] = []

    def execute(self, request: ExchangeRequest) -> ExchangeResponse:
        """Record one executed request and return the next queued response."""
        self.requests.append(request)
        return self.responses[len(self.requests) - 1]


class _RecordingProvider(MarketDataProvider):
    """Provider double that records orchestration interactions."""

    def __init__(
        self,
        *,
        provider_id: str,
        queued_pages: list[_ProviderPage] | None = None,
    ) -> None:
        super().__init__(provider_id=provider_id)
        self.queued_pages = list(queued_pages or [])
        self.build_calls: list[dict[str, object]] = []
        self.parse_calls: list[ExchangeResponse] = []

    def build_exchange_request(
        self,
        request: HistoricalCandleRequest,
        *,
        start_time_ms: int,
        end_time_ms: int,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> ExchangeRequest:
        self.build_calls.append(
            {
                "symbol": request.symbol,
                "timeframe": request.timeframe,
                "start_time_ms": start_time_ms,
                "end_time_ms": end_time_ms,
                "page_size": page_size,
                "page_token": page_token,
            }
        )
        query_params: dict[str, str | int] = {
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            "start_time_ms": start_time_ms,
            "end_time_ms": end_time_ms,
            "page_size": page_size if page_size is not None else 0,
        }
        if page_token is not None:
            query_params["page_token"] = page_token

        return ExchangeRequest(
            endpoint=ExchangeEndpoint(
                name="public_candles",
                method="GET",
                path="/v1/candles",
            ),
            query_params=query_params,
        )

    def parse_page(
        self,
        request: HistoricalCandleRequest,
        response: ExchangeResponse,
    ) -> _ProviderPage:
        del request
        self.parse_calls.append(response)
        return self.queued_pages.pop(0)


class _InvalidRequestProvider(_RecordingProvider):
    """Provider double that violates the request-construction contract."""

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
        return object()  # type: ignore[return-value]


class _InvalidPageProvider(_RecordingProvider):
    """Provider double that violates the page-parsing contract."""

    def parse_page(
        self,
        request: HistoricalCandleRequest,
        response: ExchangeResponse,
    ) -> _ProviderPage:
        del request
        del response
        return object()  # type: ignore[return-value]


class _ExplodingRequestProvider(_RecordingProvider):
    """Provider double that raises an unexpected request-construction error."""

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
        raise ValueError("bad provider request state")


class _ExplodingPageProvider(_RecordingProvider):
    """Provider double that raises an unexpected response-parsing error."""

    def parse_page(
        self,
        request: HistoricalCandleRequest,
        response: ExchangeResponse,
    ) -> _ProviderPage:
        del request
        del response
        raise RuntimeError("bad provider response state")


class _ExplodingRuntime(_RecordingRuntime):
    """Runtime double that raises an unexpected execution error."""

    def execute(self, request: ExchangeRequest) -> ExchangeResponse:
        del request
        raise RuntimeError("transport exploded")


def _make_response() -> ExchangeResponse:
    """Create one minimal exchange response for downloader tests."""
    endpoint = ExchangeEndpoint(
        name="public_candles",
        method="GET",
        path="/v1/candles",
    )
    return ExchangeResponse(
        endpoint=endpoint,
        status_code=200,
        payload={},
    )


def _make_provider_page(
    *,
    next_page_token: str | None = None,
    is_complete: bool = True,
) -> _ProviderPage:
    """Create one minimal provider page for downloader tests."""
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
        next_page_token=next_page_token,
        is_complete=is_complete,
    )


def test_market_data_downloader_is_exported_from_package_root() -> None:
    """Verify the orchestrator is part of the approved public API."""
    assert MarketDataDownloader is not None


def test_downloader_collects_windows_through_provider_and_runtime() -> None:
    """Verify the downloader orchestrates planning and execution in order."""
    provider = _RecordingProvider(
        provider_id="bybit_spot",
        queued_pages=[
            _make_provider_page(is_complete=True),
            _make_provider_page(is_complete=True),
        ],
    )
    runtime = _RecordingRuntime(
        responses=(
            _make_response(),
            _make_response(),
        )
    )
    downloader = MarketDataDownloader(
        exchange_runtime=runtime,
        provider=provider,
    )
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=120_000,
        page_size=1,
    )

    collected = downloader.collect(request)

    assert collected.provider_id == "bybit_spot"
    assert collected.total_pages == 2
    assert collected.total_requests == 2
    assert len(runtime.requests) == 2
    assert [call["start_time_ms"] for call in provider.build_calls] == [0, 60_000]
    assert [call["end_time_ms"] for call in provider.build_calls] == [60_000, 120_000]


def test_downloader_collects_multiple_provider_pages_per_window() -> None:
    """Verify provider pagination is orchestrated within one planning window."""
    provider = _RecordingProvider(
        provider_id="bybit_spot",
        queued_pages=[
            _make_provider_page(next_page_token="cursor-2", is_complete=False),
            _make_provider_page(is_complete=True),
        ],
    )
    runtime = _RecordingRuntime(
        responses=(
            _make_response(),
            _make_response(),
        )
    )
    downloader = MarketDataDownloader(
        exchange_runtime=runtime,
        provider=provider,
    )
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
        page_size=1,
    )

    collected = downloader.collect(request)

    assert collected.total_pages == 2
    assert collected.total_requests == 2
    assert provider.build_calls[0]["page_token"] is None
    assert provider.build_calls[1]["page_token"] == "cursor-2"


def test_downloader_rejects_invalid_collaborators() -> None:
    """Verify downloader collaborator validation fails fast."""
    provider = _RecordingProvider(provider_id="bybit_spot")
    runtime = _RecordingRuntime(responses=())

    with pytest.raises(
        DownloadExecutionError,
        match=(
            "MarketDataDownloader exchange_runtime must be an ExchangeRuntime "
            "instance."
        ),
    ):
        MarketDataDownloader(
            exchange_runtime=object(),  # type: ignore[arg-type]
            provider=provider,
        )

    with pytest.raises(
        DownloadExecutionError,
        match=(
            "MarketDataDownloader provider must be a MarketDataProvider "
            "instance."
        ),
    ):
        MarketDataDownloader(
            exchange_runtime=runtime,
            provider=object(),  # type: ignore[arg-type]
        )


def test_downloader_rejects_invalid_request_object() -> None:
    """Verify collect() validates the request boundary."""
    provider = _RecordingProvider(provider_id="bybit_spot")
    runtime = _RecordingRuntime(responses=())
    downloader = MarketDataDownloader(
        exchange_runtime=runtime,
        provider=provider,
    )

    with pytest.raises(
        DownloadExecutionError,
        match=(
            "MarketDataDownloader collect\\(\\) requires a "
            "HistoricalCandleRequest instance."
        ),
    ):
        downloader.collect(object())  # type: ignore[arg-type]


def test_downloader_rejects_invalid_exchange_request_output() -> None:
    """Verify provider request construction must return ExchangeRequest."""
    provider = _InvalidRequestProvider(
        provider_id="bybit_spot",
        queued_pages=[],
    )
    runtime = _RecordingRuntime(responses=())
    downloader = MarketDataDownloader(
        exchange_runtime=runtime,
        provider=provider,
    )
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
        page_size=1,
    )

    with pytest.raises(
        DownloadExecutionError,
        match=(
            "Market data provider build_exchange_request\\(\\) must return "
            "an ExchangeRequest instance."
        ),
    ):
        downloader.collect(request)


def test_downloader_rejects_invalid_provider_page_output() -> None:
    """Verify provider page parsing must return _ProviderPage."""
    provider = _InvalidPageProvider(
        provider_id="bybit_spot",
        queued_pages=[],
    )
    runtime = _RecordingRuntime(responses=(_make_response(),))
    downloader = MarketDataDownloader(
        exchange_runtime=runtime,
        provider=provider,
    )
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
        page_size=1,
    )

    with pytest.raises(
        DownloadExecutionError,
        match=(
            "Market data provider parse_page\\(\\) must return a "
            "_ProviderPage instance."
        ),
    ):
        downloader.collect(request)


def test_downloader_rejects_unprogressable_provider_pagination() -> None:
    """Verify provider pagination must remain progressable within a window."""
    provider = _RecordingProvider(
        provider_id="bybit_spot",
        queued_pages=[
            _make_provider_page(next_page_token=None, is_complete=False),
        ],
    )
    runtime = _RecordingRuntime(responses=(_make_response(),))
    downloader = MarketDataDownloader(
        exchange_runtime=runtime,
        provider=provider,
    )
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
        page_size=1,
    )

    with pytest.raises(
        DownloadExecutionError,
        match=(
            "Market data provider pagination must supply next_page_token "
            "when is_complete is False."
        ),
    ):
        downloader.collect(request)


def test_downloader_rejects_repeated_page_tokens_within_one_window() -> None:
    """Verify repeated pagination tokens fail fast to prevent token loops."""
    provider = _RecordingProvider(
        provider_id="bybit_spot",
        queued_pages=[
            _make_provider_page(next_page_token="cursor-2", is_complete=False),
            _make_provider_page(next_page_token="cursor-2", is_complete=False),
        ],
    )
    runtime = _RecordingRuntime(
        responses=(
            _make_response(),
            _make_response(),
        )
    )
    downloader = MarketDataDownloader(
        exchange_runtime=runtime,
        provider=provider,
    )
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
        page_size=1,
    )

    with pytest.raises(
        DownloadExecutionError,
        match=(
            "Market data provider pagination must not repeat page tokens "
            "within the same window."
        ),
    ):
        downloader.collect(request)


def test_downloader_download_returns_canonical_result_in_chronological_order() -> None:
    """Verify download() returns oldest-first canonical candles."""
    provider = _RecordingProvider(
        provider_id="bybit_spot",
        queued_pages=[
            _ProviderPage(
                records=(
                    _ProviderCandleRecord(
                        open_time_ms=60_000,
                        open_price="101.0",
                        high_price="102.0",
                        low_price="100.0",
                        close_price="101.5",
                        volume="11.0",
                    ),
                    _ProviderCandleRecord(
                        open_time_ms=0,
                        open_price="100.0",
                        high_price="101.0",
                        low_price="99.0",
                        close_price="100.5",
                        volume="10.0",
                    ),
                ),
                is_complete=True,
            ),
        ],
    )
    runtime = _RecordingRuntime(responses=(_make_response(),))
    downloader = MarketDataDownloader(exchange_runtime=runtime, provider=provider)
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=120_000,
    )

    result = downloader.download(request)

    assert isinstance(result, DownloadResult)
    assert [candle.open_time_ms for candle in result.candles] == [0, 60_000]
    assert result.returned_start_time_ms == 0
    assert result.returned_end_time_ms == 60_000
    assert result.total_pages == 1
    assert result.total_requests == 1
    assert result.execution_duration_seconds is not None
    assert result.execution_duration_seconds >= 0.0


def test_downloader_download_deduplicates_identical_timestamps() -> None:
    """Verify identical duplicate candle timestamps are resolved deterministically."""
    duplicate_record = _ProviderCandleRecord(
        open_time_ms=0,
        open_price="100.0",
        high_price="101.0",
        low_price="99.0",
        close_price="100.5",
        volume="10.0",
    )
    provider = _RecordingProvider(
        provider_id="bybit_spot",
        queued_pages=[
            _ProviderPage(records=(duplicate_record,), is_complete=True),
            _ProviderPage(records=(duplicate_record,), is_complete=True),
        ],
    )
    runtime = _RecordingRuntime(
        responses=(
            _make_response(),
            _make_response(),
        )
    )
    downloader = MarketDataDownloader(exchange_runtime=runtime, provider=provider)
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=120_000,
        page_size=1,
    )

    result = downloader.download(request)

    assert [candle.open_time_ms for candle in result.candles] == [0]
    assert result.total_pages == 2
    assert result.total_requests == 2


def test_downloader_download_rejects_conflicting_duplicate_timestamps() -> None:
    """Verify duplicate timestamps with conflicting values fail normalization."""
    provider = _RecordingProvider(
        provider_id="bybit_spot",
        queued_pages=[
            _ProviderPage(
                records=(
                    _ProviderCandleRecord(
                        open_time_ms=0,
                        open_price="100.0",
                        high_price="101.0",
                        low_price="99.0",
                        close_price="100.5",
                        volume="10.0",
                    ),
                ),
                is_complete=True,
            ),
            _ProviderPage(
                records=(
                    _ProviderCandleRecord(
                        open_time_ms=0,
                        open_price="100.0",
                        high_price="101.5",
                        low_price="99.0",
                        close_price="100.5",
                        volume="10.0",
                    ),
                ),
                is_complete=True,
            ),
        ],
    )
    runtime = _RecordingRuntime(
        responses=(
            _make_response(),
            _make_response(),
        )
    )
    downloader = MarketDataDownloader(exchange_runtime=runtime, provider=provider)
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=120_000,
        page_size=1,
    )

    with pytest.raises(
        NormalizationError,
        match=(
            "Duplicate candle timestamps must contain identical canonical values."
        ),
    ):
        downloader.download(request)


def test_downloader_download_rejects_candles_outside_requested_interval() -> None:
    """Verify provider records outside the request interval fail normalization."""
    provider = _RecordingProvider(
        provider_id="bybit_spot",
        queued_pages=[
            _ProviderPage(
                records=(
                    _ProviderCandleRecord(
                        open_time_ms=120_000,
                        open_price="100.0",
                        high_price="101.0",
                        low_price="99.0",
                        close_price="100.5",
                        volume="10.0",
                    ),
                ),
                is_complete=True,
            ),
        ],
    )
    runtime = _RecordingRuntime(responses=(_make_response(),))
    downloader = MarketDataDownloader(exchange_runtime=runtime, provider=provider)
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=120_000,
    )

    with pytest.raises(
        NormalizationError,
        match=(
            "Collected provider candle timestamps must stay within the "
            "requested interval."
        ),
    ):
        downloader.download(request)


def test_downloader_download_supports_empty_collections() -> None:
    """Verify download() can return an empty canonical result."""
    provider = _RecordingProvider(
        provider_id="bybit_spot",
        queued_pages=[
            _ProviderPage(records=(), is_complete=True),
        ],
    )
    runtime = _RecordingRuntime(responses=(_make_response(),))
    downloader = MarketDataDownloader(exchange_runtime=runtime, provider=provider)
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
    )

    result = downloader.download(request)

    assert result.candles == ()
    assert result.returned_start_time_ms is None
    assert result.returned_end_time_ms is None


def test_downloader_surfaces_planning_failures_through_repository_error() -> None:
    """Verify planning failures remain repository-native."""
    provider = _RecordingProvider(
        provider_id="bybit_spot",
        queued_pages=[],
    )
    runtime = _RecordingRuntime(responses=())
    downloader = MarketDataDownloader(exchange_runtime=runtime, provider=provider)
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1x",
        start_time_ms=0,
        end_time_ms=60_000,
    )

    with pytest.raises(
        DownloadPlanningError,
        match="Download planning does not support timeframe unit 'x'.",
    ):
        downloader.download(request)


def test_downloader_normalizes_provider_request_failures() -> None:
    """Verify provider request-construction exceptions become repository-native."""
    provider = _ExplodingRequestProvider(
        provider_id="bybit_spot",
        queued_pages=[],
    )
    runtime = _RecordingRuntime(responses=())
    downloader = MarketDataDownloader(exchange_runtime=runtime, provider=provider)
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="Market data provider build_exchange_request\\(\\) failed\\.",
    ) as exc_info:
        downloader.download(request)

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_downloader_normalizes_runtime_failures() -> None:
    """Verify runtime execution exceptions become repository-native."""
    provider = _RecordingProvider(
        provider_id="bybit_spot",
        queued_pages=[_make_provider_page(is_complete=True)],
    )
    runtime = _ExplodingRuntime(responses=())
    downloader = MarketDataDownloader(exchange_runtime=runtime, provider=provider)
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
    )

    with pytest.raises(
        DownloadExecutionError,
        match="Exchange runtime execution failed\\.",
    ) as exc_info:
        downloader.download(request)

    assert isinstance(exc_info.value.__cause__, RuntimeError)


def test_downloader_normalizes_provider_parse_failures() -> None:
    """Verify provider parse exceptions become repository-native."""
    provider = _ExplodingPageProvider(
        provider_id="bybit_spot",
        queued_pages=[],
    )
    runtime = _RecordingRuntime(responses=(_make_response(),))
    downloader = MarketDataDownloader(exchange_runtime=runtime, provider=provider)
    request = HistoricalCandleRequest(
        symbol="BTCUSDT",
        timeframe="1m",
        start_time_ms=0,
        end_time_ms=60_000,
    )

    with pytest.raises(
        ProviderConfigurationError,
        match="Market data provider parse_page\\(\\) failed\\.",
    ) as exc_info:
        downloader.download(request)

    assert isinstance(exc_info.value.__cause__, RuntimeError)
