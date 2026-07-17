"""Internal download planning artifacts."""

from __future__ import annotations

from dataclasses import dataclass

from python_market_data_downloader.models import HistoricalCandleRequest


@dataclass(frozen=True, slots=True)
class _DownloadWindow:
    """Describe one deterministic historical request window.

    Purpose:
        Represent one planned sub-interval of a historical candle request
        before any execution occurs.

    Parameters:
        index: Zero-based deterministic window index.
        start_time_ms: Inclusive UTC epoch millisecond window start time.
        end_time_ms: Exclusive UTC epoch millisecond window end time.
        page_size: Optional page-size hint propagated from the request.

    Attributes:
        index: Zero-based deterministic window index.
        start_time_ms: Inclusive UTC epoch millisecond window start time.
        end_time_ms: Exclusive UTC epoch millisecond window end time.
        page_size: Optional page-size hint propagated from the request.

    Raises:
        ValueError: If the window interval is structurally invalid.
        TypeError: If the window metadata uses unsupported types.

    Usage Notes:
        Windows are immutable and contain no execution state.
    """

    index: int
    start_time_ms: int
    end_time_ms: int
    page_size: int | None = None

    def __post_init__(self) -> None:
        """Validate window invariants."""
        if isinstance(self.index, bool) or not isinstance(self.index, int):
            raise TypeError("Download window index must be an integer.")

        if self.index < 0:
            raise ValueError("Download window index must be non-negative.")

        if isinstance(self.start_time_ms, bool) or not isinstance(
            self.start_time_ms,
            int,
        ):
            raise TypeError("Download window start_time_ms must be an integer.")

        if isinstance(self.end_time_ms, bool) or not isinstance(self.end_time_ms, int):
            raise TypeError("Download window end_time_ms must be an integer.")

        if self.start_time_ms < 0 or self.end_time_ms < 0:
            raise ValueError(
                "Download window timestamps must be greater than or equal to zero."
            )

        if self.end_time_ms <= self.start_time_ms:
            raise ValueError(
                "Download window end_time_ms must be greater than start_time_ms."
            )

        if self.page_size is not None:
            if isinstance(self.page_size, bool) or not isinstance(self.page_size, int):
                raise TypeError("Download window page_size must be an integer.")

            if self.page_size <= 0:
                raise ValueError("Download window page_size must be greater than zero.")


@dataclass(frozen=True, slots=True)
class _DownloadPlan:
    """Describe one deterministic internal download plan.

    Purpose:
        Capture the immutable planning output used later by the downloader
        orchestrator to execute a historical candle request.

    Parameters:
        request: Original canonical historical request.
        provider_id: Stable provider identifier used for planning context.
        timeframe_ms: Resolved candle timeframe duration in milliseconds.
        windows: Deterministic non-overlapping request windows.

    Attributes:
        request: Original canonical historical request.
        provider_id: Stable provider identifier used for planning context.
        timeframe_ms: Resolved candle timeframe duration in milliseconds.
        windows: Deterministic non-overlapping request windows.

    Raises:
        ValueError: If the plan is structurally inconsistent.
        TypeError: If the plan metadata uses unsupported types.

    Usage Notes:
        Plans are internal and remain outside the package root public API.
    """

    request: HistoricalCandleRequest
    provider_id: str
    timeframe_ms: int
    windows: tuple[_DownloadWindow, ...]

    def __post_init__(self) -> None:
        """Validate plan invariants."""
        if not isinstance(self.request, HistoricalCandleRequest):
            raise TypeError(
                "Download plan request must be a HistoricalCandleRequest instance."
            )

        if not isinstance(self.provider_id, str):
            raise TypeError("Download plan provider_id must be a string.")

        normalized_provider_id = self.provider_id.strip()
        if not normalized_provider_id:
            raise ValueError("Download plan provider_id must be non-empty.")
        object.__setattr__(self, "provider_id", normalized_provider_id)

        if isinstance(self.timeframe_ms, bool) or not isinstance(
            self.timeframe_ms,
            int,
        ):
            raise TypeError("Download plan timeframe_ms must be an integer.")

        if self.timeframe_ms <= 0:
            raise ValueError("Download plan timeframe_ms must be greater than zero.")

        if not isinstance(self.windows, tuple):
            raise TypeError("Download plan windows must be a tuple.")

        if not self.windows:
            raise ValueError("Download plan windows must be non-empty.")

        expected_start = self.request.start_time_ms
        previous_index = -1
        for window in self.windows:
            if not isinstance(window, _DownloadWindow):
                raise TypeError(
                    "Download plan windows must contain _DownloadWindow instances."
                )

            if window.index != previous_index + 1:
                raise ValueError(
                    "Download plan windows must use contiguous zero-based indexes."
                )

            if window.start_time_ms != expected_start:
                raise ValueError(
                    "Download plan windows must provide contiguous non-overlapping "
                    "coverage."
                )

            if window.page_size != self.request.page_size:
                raise ValueError(
                    "Download plan window page_size must match the original request."
                )

            previous_index = window.index
            expected_start = window.end_time_ms

        if self.windows[0].start_time_ms != self.request.start_time_ms:
            raise ValueError(
                "Download plan must start at the request start_time_ms boundary."
            )

        if self.windows[-1].end_time_ms != self.request.end_time_ms:
            raise ValueError(
                "Download plan must end at the request end_time_ms boundary."
            )
