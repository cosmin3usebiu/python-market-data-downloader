"""Deterministic download planning helpers."""

from __future__ import annotations

from math import ceil

from python_market_data_downloader.download_plan import _DownloadPlan, _DownloadWindow
from python_market_data_downloader.errors import DownloadPlanningError
from python_market_data_downloader.models import HistoricalCandleRequest
from python_market_data_downloader.provider import MarketDataProvider

_TIMEFRAME_MULTIPLIERS_MS: dict[str, int] = {
    "s": 1_000,
    "m": 60_000,
    "h": 3_600_000,
    "d": 86_400_000,
    "w": 604_800_000,
}


def _build_download_plan(
    request: HistoricalCandleRequest,
    provider: MarketDataProvider,
) -> _DownloadPlan:
    """Build a deterministic internal download plan.

    Args:
        request: Canonical historical candle request to plan.
        provider: Provider contract used for planning context.

    Returns:
        One immutable download plan with deterministic, non-overlapping
        windows.

    Raises:
        DownloadPlanningError: If the request cannot be planned
            deterministically.
    """
    if not isinstance(request, HistoricalCandleRequest):
        raise DownloadPlanningError(
            "Download planning requires a HistoricalCandleRequest instance."
        )

    if not isinstance(provider, MarketDataProvider):
        raise DownloadPlanningError(
            "Download planning requires a MarketDataProvider instance."
        )

    timeframe_ms = _resolve_timeframe_ms(request.timeframe)
    window_span_ms = _resolve_window_span_ms(
        request=request,
        timeframe_ms=timeframe_ms,
    )
    total_windows = _calculate_window_count(
        request=request,
        window_span_ms=window_span_ms,
    )
    _validate_max_requests(
        request=request,
        total_windows=total_windows,
    )

    windows: list[_DownloadWindow] = []
    next_start_time_ms = request.start_time_ms
    for index in range(total_windows):
        next_end_time_ms = min(next_start_time_ms + window_span_ms, request.end_time_ms)
        windows.append(
            _DownloadWindow(
                index=index,
                start_time_ms=next_start_time_ms,
                end_time_ms=next_end_time_ms,
                page_size=request.page_size,
            )
        )
        next_start_time_ms = next_end_time_ms

    return _DownloadPlan(
        request=request,
        provider_id=provider.provider_id,
        timeframe_ms=timeframe_ms,
        windows=tuple(windows),
    )


def _get_next_window(
    plan: _DownloadPlan,
    *,
    completed_windows: int,
) -> _DownloadWindow:
    """Return the next deterministic window to execute.

    Args:
        plan: Immutable internal download plan.
        completed_windows: Number of fully completed windows.

    Returns:
        The next window to execute.

    Raises:
        DownloadPlanningError: If the completion state is invalid or the plan
            is already complete.
    """
    _validate_completion_index(plan, completed_windows)

    if completed_windows >= len(plan.windows):
        raise DownloadPlanningError("Download plan is already complete.")

    return plan.windows[completed_windows]


def _is_plan_complete(
    plan: _DownloadPlan,
    *,
    completed_windows: int,
) -> bool:
    """Return whether all plan windows have been completed.

    Args:
        plan: Immutable internal download plan.
        completed_windows: Number of fully completed windows.

    Returns:
        ``True`` when all windows are complete, otherwise ``False``.

    Raises:
        DownloadPlanningError: If the completion state is invalid.
    """
    _validate_completion_index(plan, completed_windows)
    return completed_windows == len(plan.windows)


def _resolve_timeframe_ms(timeframe: str) -> int:
    """Resolve a candle timeframe string into milliseconds."""
    if not isinstance(timeframe, str):
        raise DownloadPlanningError("Download planning timeframe must be a string.")

    normalized_timeframe = timeframe.strip().lower()
    if len(normalized_timeframe) < 2:
        raise DownloadPlanningError(
            "Download planning timeframe must use the form <count><unit>."
        )

    unit = normalized_timeframe[-1]
    multiplier_ms = _TIMEFRAME_MULTIPLIERS_MS.get(unit)
    if multiplier_ms is None:
        raise DownloadPlanningError(
            f"Download planning does not support timeframe unit '{unit}'."
        )

    quantity_text = normalized_timeframe[:-1]
    if not quantity_text.isdigit():
        raise DownloadPlanningError(
            "Download planning timeframe quantity must be a positive integer."
        )

    quantity = int(quantity_text)
    if quantity <= 0:
        raise DownloadPlanningError(
            "Download planning timeframe quantity must be greater than zero."
        )

    return quantity * multiplier_ms


def _resolve_window_span_ms(
    *,
    request: HistoricalCandleRequest,
    timeframe_ms: int,
) -> int:
    """Resolve the deterministic planning window span in milliseconds."""
    if request.page_size is None:
        return request.end_time_ms - request.start_time_ms

    return request.page_size * timeframe_ms


def _calculate_window_count(
    *,
    request: HistoricalCandleRequest,
    window_span_ms: int,
) -> int:
    """Calculate the number of windows required for deterministic coverage."""
    if window_span_ms <= 0:
        raise DownloadPlanningError(
            "Download planning window span must be greater than zero."
        )

    interval_ms = request.end_time_ms - request.start_time_ms
    return ceil(interval_ms / window_span_ms)


def _validate_max_requests(
    *,
    request: HistoricalCandleRequest,
    total_windows: int,
) -> None:
    """Validate that the request can be satisfied within max_requests."""
    if request.max_requests is None:
        return

    if total_windows > request.max_requests:
        raise DownloadPlanningError(
            "Download planning requires more windows than request max_requests "
            "allows."
        )


def _validate_completion_index(
    plan: _DownloadPlan,
    completed_windows: int,
) -> None:
    """Validate one deterministic completed-window count."""
    if not isinstance(plan, _DownloadPlan):
        raise DownloadPlanningError("Completion checks require a _DownloadPlan.")

    if isinstance(completed_windows, bool) or not isinstance(completed_windows, int):
        raise DownloadPlanningError(
            "Completion checks require completed_windows to be an integer."
        )

    if completed_windows < 0:
        raise DownloadPlanningError(
            "Completion checks require completed_windows to be non-negative."
        )

    if completed_windows > len(plan.windows):
        raise DownloadPlanningError(
            "Completion checks require completed_windows to stay within the "
            "planned window count."
        )
