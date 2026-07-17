"""Downloader orchestration definitions."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from python_exchange_integration_runtime import (
    ExchangeRequest,
    ExchangeResponse,
    ExchangeRuntime,
)

from python_market_data_downloader.download_plan import _DownloadPlan, _DownloadWindow
from python_market_data_downloader.errors import (
    DownloadExecutionError,
    DownloadPlanningError,
    ProviderConfigurationError,
)
from python_market_data_downloader.models import DownloadResult, HistoricalCandleRequest
from python_market_data_downloader.normalization import _normalize_collected_download
from python_market_data_downloader.planning import (
    _build_download_plan,
    _get_next_window,
    _is_plan_complete,
)
from python_market_data_downloader.provider import MarketDataProvider, _ProviderPage


@dataclass(frozen=True, slots=True)
class _CollectedPage:
    """Describe one collected raw execution page.

    Purpose:
        Preserve the immutable execution artifacts produced for one planned
        provider page before canonical normalization occurs.

    Parameters:
        window: Deterministic planning window being executed.
        exchange_request: Exchange request executed through the exchange
            runtime.
        exchange_response: Exchange response returned by the exchange runtime.
        provider_page: Provider-native parsed page artifact.
        page_token: Optional provider-specific pagination token used to build
            the request.

    Attributes:
        window: Deterministic planning window being executed.
        exchange_request: Exchange request executed through the exchange
            runtime.
        exchange_response: Exchange response returned by the exchange runtime.
        provider_page: Provider-native parsed page artifact.
        page_token: Optional provider-specific pagination token used to build
            the request.

    Raises:
        TypeError: If any execution artifact uses an unsupported type.

    Usage Notes:
        This artifact is internal and is consumed by later normalization
        stages.
    """

    window: _DownloadWindow
    exchange_request: ExchangeRequest
    exchange_response: ExchangeResponse
    provider_page: _ProviderPage
    page_token: str | None = None

    def __post_init__(self) -> None:
        """Validate collected page invariants."""
        if not isinstance(self.window, _DownloadWindow):
            raise TypeError("Collected page window must be a _DownloadWindow.")

        if not isinstance(self.exchange_request, ExchangeRequest):
            raise TypeError(
                "Collected page exchange_request must be an ExchangeRequest."
            )

        if not isinstance(self.exchange_response, ExchangeResponse):
            raise TypeError(
                "Collected page exchange_response must be an ExchangeResponse."
            )

        if not isinstance(self.provider_page, _ProviderPage):
            raise TypeError("Collected page provider_page must be a _ProviderPage.")

        if self.page_token is not None and not isinstance(self.page_token, str):
            raise TypeError("Collected page page_token must be a string or None.")


@dataclass(frozen=True, slots=True)
class _CollectedDownload:
    """Describe one raw collected download execution.

    Purpose:
        Preserve the immutable orchestrator output produced before canonical
        normalization and final result assembly occur.

    Parameters:
        request: Original historical request being executed.
        provider_id: Provider identifier used during execution.
        plan: Deterministic internal download plan.
        pages: Collected raw execution pages in execution order.
        total_pages: Number of provider pages collected.
        total_requests: Number of runtime requests executed.

    Attributes:
        request: Original historical request being executed.
        provider_id: Provider identifier used during execution.
        plan: Deterministic internal download plan.
        pages: Collected raw execution pages in execution order.
        total_pages: Number of provider pages collected.
        total_requests: Number of runtime requests executed.

    Raises:
        TypeError: If collected execution metadata uses unsupported types.
        ValueError: If collected execution metadata is structurally invalid.

    Usage Notes:
        This artifact remains internal and will be consumed by the later
        normalization milestone.
    """

    request: HistoricalCandleRequest
    provider_id: str
    plan: _DownloadPlan
    pages: tuple[_CollectedPage, ...]
    total_pages: int
    total_requests: int

    def __post_init__(self) -> None:
        """Validate collected download invariants."""
        if not isinstance(self.request, HistoricalCandleRequest):
            raise TypeError(
                "Collected download request must be a HistoricalCandleRequest."
            )

        if not isinstance(self.provider_id, str):
            raise TypeError("Collected download provider_id must be a string.")

        normalized_provider_id = self.provider_id.strip()
        if not normalized_provider_id:
            raise ValueError("Collected download provider_id must be non-empty.")
        object.__setattr__(self, "provider_id", normalized_provider_id)

        if not isinstance(self.plan, _DownloadPlan):
            raise TypeError("Collected download plan must be a _DownloadPlan.")

        if not isinstance(self.pages, tuple):
            raise TypeError("Collected download pages must be a tuple.")

        for page in self.pages:
            if not isinstance(page, _CollectedPage):
                raise TypeError(
                    "Collected download pages must contain _CollectedPage instances."
                )

        if self.total_pages != len(self.pages):
            raise ValueError(
                "Collected download total_pages must match the number of pages."
            )

        if isinstance(self.total_pages, bool) or not isinstance(self.total_pages, int):
            raise TypeError("Collected download total_pages must be an integer.")

        if isinstance(self.total_requests, bool) or not isinstance(
            self.total_requests,
            int,
        ):
            raise TypeError("Collected download total_requests must be an integer.")

        if self.total_pages < 0 or self.total_requests < 0:
            raise ValueError(
                "Collected download page and request counts must be non-negative."
            )


@dataclass(slots=True)
class MarketDataDownloader:
    """Coordinate raw market-data page acquisition through the platform stack.

    Purpose:
        Orchestrate deterministic planning, provider request construction,
        exchange runtime execution, and provider page parsing while delegating
        canonical result assembly to the internal normalization layer.

    Parameters:
        exchange_runtime: Exchange runtime used for request execution.
        provider: Provider contract used for request construction and response
            parsing.

    Attributes:
        exchange_runtime: Exchange runtime used for request execution.
        provider: Provider contract used for request construction and response
            parsing.

    Raises:
        DownloadExecutionError: If downloader collaborators are invalid.

    Usage Notes:
        This class owns orchestration only. Planning remains pure, providers
        remain exchange-specific, and canonical normalization is delegated to
        the internal normalization subsystem.
    """

    exchange_runtime: ExchangeRuntime
    provider: MarketDataProvider

    def __post_init__(self) -> None:
        """Validate downloader collaborators."""
        if not isinstance(self.exchange_runtime, ExchangeRuntime):
            raise DownloadExecutionError(
                "MarketDataDownloader exchange_runtime must be an ExchangeRuntime "
                "instance."
            )

        if not isinstance(self.provider, MarketDataProvider):
            raise DownloadExecutionError(
                "MarketDataDownloader provider must be a MarketDataProvider "
                "instance."
            )

    def collect(self, request: HistoricalCandleRequest) -> _CollectedDownload:
        """Collect raw provider pages for one historical request.

        Args:
            request: Canonical historical candle request to execute.

        Returns:
            One immutable internal collected-download artifact.

        Raises:
            DownloadExecutionError: If collaborator outputs violate
                orchestration contracts.
        """
        if not isinstance(request, HistoricalCandleRequest):
            raise DownloadExecutionError(
                "MarketDataDownloader collect() requires a "
                "HistoricalCandleRequest instance."
            )

        plan = self._build_plan(request)
        collected_pages: list[_CollectedPage] = []
        completed_windows = 0

        while (
            self._is_plan_complete(plan, completed_windows=completed_windows)
            is False
        ):
            window = self._get_next_window(plan, completed_windows=completed_windows)
            collected_pages.extend(self._collect_window(request=request, window=window))
            completed_windows += 1

        try:
            return _CollectedDownload(
                request=request,
                provider_id=self.provider.provider_id,
                plan=plan,
                pages=tuple(collected_pages),
                total_pages=len(collected_pages),
                total_requests=len(collected_pages),
            )
        except (TypeError, ValueError) as exc:
            raise DownloadExecutionError(
                "Collected download artifacts must be structurally valid."
            ) from exc

    def download(self, request: HistoricalCandleRequest) -> DownloadResult:
        """Download canonical historical candles for one request.

        Args:
            request: Canonical historical candle request to execute.

        Returns:
            One immutable canonical download result.

        Raises:
            DownloadExecutionError: If orchestration collaborators violate
                downloader contracts.
            NormalizationError: If collected provider records cannot be
                normalized into canonical candles.
        """
        start_time = perf_counter()
        collected_download = self.collect(request)
        duration_seconds = perf_counter() - start_time
        return _normalize_collected_download(
            collected_download,
            execution_duration_seconds=duration_seconds,
        )

    def _collect_window(
        self,
        *,
        request: HistoricalCandleRequest,
        window: _DownloadWindow,
    ) -> list[_CollectedPage]:
        """Collect all provider pages for one deterministic window."""
        collected_pages: list[_CollectedPage] = []
        page_token: str | None = None
        seen_page_tokens: set[str] = set()

        while True:
            exchange_request = self._build_exchange_request(
                request=request,
                window=window,
                page_token=page_token,
            )
            if not isinstance(exchange_request, ExchangeRequest):
                raise DownloadExecutionError(
                    "Market data provider build_exchange_request() must return "
                    "an ExchangeRequest instance."
                )

            exchange_response = self._execute_exchange_request(exchange_request)
            if not isinstance(exchange_response, ExchangeResponse):
                raise DownloadExecutionError(
                    "ExchangeRuntime execute() must return an ExchangeResponse "
                    "instance."
                )

            provider_page = self._parse_provider_page(
                request=request,
                exchange_response=exchange_response,
            )
            if not isinstance(provider_page, _ProviderPage):
                raise DownloadExecutionError(
                    "Market data provider parse_page() must return a "
                    "_ProviderPage instance."
                )

            collected_pages.append(
                _CollectedPage(
                    window=window,
                    exchange_request=exchange_request,
                    exchange_response=exchange_response,
                    provider_page=provider_page,
                    page_token=page_token,
                )
            )

            if provider_page.is_complete:
                return collected_pages

            next_page_token = provider_page.next_page_token
            if next_page_token is None:
                raise DownloadExecutionError(
                    "Market data provider pagination must supply next_page_token "
                    "when is_complete is False."
                )

            if next_page_token in seen_page_tokens:
                raise DownloadExecutionError(
                    "Market data provider pagination must not repeat page tokens "
                    "within the same window."
                )

            seen_page_tokens.add(next_page_token)
            page_token = next_page_token

    def _build_plan(self, request: HistoricalCandleRequest) -> _DownloadPlan:
        """Build one internal download plan with repository error normalization."""
        try:
            return _build_download_plan(request, self.provider)
        except DownloadPlanningError:
            raise
        except Exception as exc:
            raise DownloadPlanningError(
                "Download planning failed unexpectedly."
            ) from exc

    def _is_plan_complete(
        self,
        plan: _DownloadPlan,
        *,
        completed_windows: int,
    ) -> bool:
        """Return plan completion state with repository error normalization."""
        try:
            return _is_plan_complete(plan, completed_windows=completed_windows)
        except DownloadPlanningError:
            raise
        except Exception as exc:
            raise DownloadPlanningError(
                "Download plan completion checks failed unexpectedly."
            ) from exc

    def _get_next_window(
        self,
        plan: _DownloadPlan,
        *,
        completed_windows: int,
    ) -> _DownloadWindow:
        """Return the next window with repository error normalization."""
        try:
            return _get_next_window(plan, completed_windows=completed_windows)
        except DownloadPlanningError:
            raise
        except Exception as exc:
            raise DownloadPlanningError(
                "Download plan window resolution failed unexpectedly."
            ) from exc

    def _build_exchange_request(
        self,
        *,
        request: HistoricalCandleRequest,
        window: _DownloadWindow,
        page_token: str | None,
    ) -> ExchangeRequest:
        """Build one provider request with provider error normalization."""
        try:
            return self.provider.build_exchange_request(
                request,
                start_time_ms=window.start_time_ms,
                end_time_ms=window.end_time_ms,
                page_size=window.page_size,
                page_token=page_token,
            )
        except ProviderConfigurationError:
            raise
        except Exception as exc:
            raise ProviderConfigurationError(
                "Market data provider build_exchange_request() failed."
            ) from exc

    def _execute_exchange_request(
        self,
        exchange_request: ExchangeRequest,
    ) -> ExchangeResponse:
        """Execute one exchange request with repository error normalization."""
        try:
            return self.exchange_runtime.execute(exchange_request)
        except DownloadExecutionError:
            raise
        except Exception as exc:
            raise DownloadExecutionError(
                "Exchange runtime execution failed."
            ) from exc

    def _parse_provider_page(
        self,
        *,
        request: HistoricalCandleRequest,
        exchange_response: ExchangeResponse,
    ) -> _ProviderPage:
        """Parse one provider page with provider error normalization."""
        try:
            return self.provider.parse_page(request, exchange_response)
        except ProviderConfigurationError:
            raise
        except Exception as exc:
            raise ProviderConfigurationError(
                "Market data provider parse_page() failed."
            ) from exc
