"""Canonical normalization for collected market-data downloads."""

from __future__ import annotations

from python_market_data_downloader.errors import NormalizationError
from python_market_data_downloader.models import (
    DownloadResult,
    HistoricalCandle,
)


def _normalize_collected_download(
    collected_download: object,
    *,
    execution_duration_seconds: float | None = None,
) -> DownloadResult:
    """Normalize one collected download into the canonical result contract.

    Args:
        collected_download: Internal collected download artifact produced by the
            downloader orchestration layer.
        execution_duration_seconds: Optional measured workflow execution
            duration.

    Returns:
        One immutable canonical download result.

    Raises:
        NormalizationError: If collected download artifacts violate
            normalization rules.
    """
    from python_market_data_downloader.downloader import _CollectedDownload

    if not isinstance(collected_download, _CollectedDownload):
        raise NormalizationError(
            "Collected download normalization requires a _CollectedDownload "
            "instance."
        )

    try:
        normalized_candles = _normalize_candles(collected_download)
        returned_start_time_ms = (
            normalized_candles[0].open_time_ms if normalized_candles else None
        )
        returned_end_time_ms = (
            normalized_candles[-1].open_time_ms if normalized_candles else None
        )
        return DownloadResult(
            request=collected_download.request,
            provider_id=collected_download.provider_id,
            candles=normalized_candles,
            returned_start_time_ms=returned_start_time_ms,
            returned_end_time_ms=returned_end_time_ms,
            total_pages=collected_download.total_pages,
            total_requests=collected_download.total_requests,
            execution_duration_seconds=execution_duration_seconds,
        )
    except NormalizationError:
        raise
    except (TypeError, ValueError) as exc:
        raise NormalizationError(
            "Collected download normalization produced an invalid DownloadResult."
        ) from exc
    except Exception as exc:
        raise NormalizationError(
            "Collected download normalization failed unexpectedly."
        ) from exc


def _normalize_candles(collected_download: object) -> tuple[HistoricalCandle, ...]:
    """Normalize collected provider records into canonical candles."""
    collected_candles = _collect_canonical_candles(collected_download)
    ordered_candles = tuple(
        sorted(
            collected_candles,
            key=lambda candle: candle.open_time_ms,
        )
    )
    return _deduplicate_candles(ordered_candles)


def _collect_canonical_candles(
    collected_download: object,
) -> tuple[HistoricalCandle, ...]:
    """Build canonical candles from collected provider-native records."""
    request = collected_download.request
    provider_id = collected_download.provider_id
    normalized_candles: list[HistoricalCandle] = []

    for page in collected_download.pages:
        for record in page.provider_page.records:
            open_time_ms = record.open_time_ms
            if (
                open_time_ms < request.start_time_ms
                or open_time_ms >= request.end_time_ms
            ):
                raise NormalizationError(
                    "Collected provider candle timestamps must stay within the "
                    "requested interval."
                )

            try:
                normalized_candles.append(
                    HistoricalCandle(
                        provider_id=provider_id,
                        symbol=request.symbol,
                        timeframe=request.timeframe,
                        open_time_ms=record.open_time_ms,
                        open_price=record.open_price,
                        high_price=record.high_price,
                        low_price=record.low_price,
                        close_price=record.close_price,
                        volume=record.volume,
                    )
                )
            except (TypeError, ValueError) as exc:
                raise NormalizationError(
                    "Collected provider records must normalize into valid "
                    "HistoricalCandle instances."
                ) from exc

    return tuple(normalized_candles)


def _deduplicate_candles(
    candles: tuple[HistoricalCandle, ...],
) -> tuple[HistoricalCandle, ...]:
    """Resolve duplicate candle timestamps deterministically."""
    deduplicated_candles: list[HistoricalCandle] = []
    seen_candles_by_timestamp: dict[int, HistoricalCandle] = {}

    for candle in candles:
        existing_candle = seen_candles_by_timestamp.get(candle.open_time_ms)
        if existing_candle is None:
            seen_candles_by_timestamp[candle.open_time_ms] = candle
            deduplicated_candles.append(candle)
            continue

        if existing_candle != candle:
            raise NormalizationError(
                "Duplicate candle timestamps must contain identical canonical values."
            )

    return tuple(deduplicated_candles)
