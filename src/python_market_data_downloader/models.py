"""Immutable public models for market-data download workflows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True, slots=True)
class HistoricalCandleRequest:
    """Describe one bounded historical candle download request.

    Purpose:
        Represent the immutable user-facing request used to describe one
        historical candle acquisition workflow.

    Parameters:
        symbol: Stable market symbol to download.
        timeframe: Stable candle timeframe identifier.
        start_time_ms: Inclusive UTC epoch millisecond start time.
        end_time_ms: Exclusive UTC epoch millisecond end time.
        page_size: Optional provider page-size hint.
        max_requests: Optional upper bound on executed page requests.

    Attributes:
        symbol: Stable market symbol to download.
        timeframe: Stable candle timeframe identifier.
        start_time_ms: Inclusive UTC epoch millisecond start time.
        end_time_ms: Exclusive UTC epoch millisecond end time.
        page_size: Optional provider page-size hint.
        max_requests: Optional upper bound on executed page requests.

    Raises:
        ValueError: If request metadata is structurally invalid.
        TypeError: If request metadata uses unsupported types.

    Usage Notes:
        This object is immutable and contains no execution behavior.
    """

    symbol: str
    timeframe: str
    start_time_ms: int
    end_time_ms: int
    page_size: int | None = None
    max_requests: int | None = None

    def __post_init__(self) -> None:
        """Validate request invariants."""
        object.__setattr__(self, "symbol", _normalize_identifier(self.symbol, "symbol"))
        object.__setattr__(
            self,
            "timeframe",
            _normalize_identifier(self.timeframe, "timeframe"),
        )
        object.__setattr__(
            self,
            "start_time_ms",
            _normalize_timestamp(self.start_time_ms, "start_time_ms"),
        )
        object.__setattr__(
            self,
            "end_time_ms",
            _normalize_timestamp(self.end_time_ms, "end_time_ms"),
        )
        object.__setattr__(
            self,
            "page_size",
            _normalize_positive_int(
                self.page_size,
                "page_size",
                allow_none=True,
            ),
        )
        object.__setattr__(
            self,
            "max_requests",
            _normalize_positive_int(
                self.max_requests,
                "max_requests",
                allow_none=True,
            ),
        )

        if self.end_time_ms <= self.start_time_ms:
            raise ValueError(
                "Historical candle request end_time_ms must be greater than "
                "start_time_ms."
            )


@dataclass(frozen=True, slots=True)
class HistoricalCandle:
    """Describe one canonical normalized candle record.

    Purpose:
        Represent the immutable repository-wide candle format returned by the
        downloader after canonical normalization.

    Parameters:
        provider_id: Stable market-data provider identifier.
        symbol: Stable market symbol.
        timeframe: Stable candle timeframe identifier.
        open_time_ms: UTC epoch millisecond candle open time.
        open_price: Canonical open price string.
        high_price: Canonical high price string.
        low_price: Canonical low price string.
        close_price: Canonical close price string.
        volume: Optional canonical volume string.

    Attributes:
        provider_id: Stable market-data provider identifier.
        symbol: Stable market symbol.
        timeframe: Stable candle timeframe identifier.
        open_time_ms: UTC epoch millisecond candle open time.
        open_price: Canonical open price string.
        high_price: Canonical high price string.
        low_price: Canonical low price string.
        close_price: Canonical close price string.
        volume: Optional canonical volume string.

    Raises:
        ValueError: If candle values are structurally invalid.
        TypeError: If candle values use unsupported types.

    Usage Notes:
        Prices and volume remain strings so downstream systems can preserve
        exchange precision without float coercion.
    """

    provider_id: str
    symbol: str
    timeframe: str
    open_time_ms: int
    open_price: str
    high_price: str
    low_price: str
    close_price: str
    volume: str | None = None

    def __post_init__(self) -> None:
        """Validate candle invariants."""
        object.__setattr__(
            self,
            "provider_id",
            _normalize_identifier(self.provider_id, "provider_id"),
        )
        object.__setattr__(self, "symbol", _normalize_identifier(self.symbol, "symbol"))
        object.__setattr__(
            self,
            "timeframe",
            _normalize_identifier(self.timeframe, "timeframe"),
        )
        object.__setattr__(
            self,
            "open_time_ms",
            _normalize_timestamp(self.open_time_ms, "open_time_ms"),
        )

        open_decimal = _normalize_decimal_text(self.open_price, "open_price")
        high_decimal = _normalize_decimal_text(self.high_price, "high_price")
        low_decimal = _normalize_decimal_text(self.low_price, "low_price")
        close_decimal = _normalize_decimal_text(self.close_price, "close_price")

        object.__setattr__(self, "open_price", open_decimal)
        object.__setattr__(self, "high_price", high_decimal)
        object.__setattr__(self, "low_price", low_decimal)
        object.__setattr__(self, "close_price", close_decimal)
        object.__setattr__(
            self,
            "volume",
            _normalize_decimal_text(
                self.volume,
                "volume",
                allow_none=True,
                allow_zero=True,
            ),
        )

        low_value = Decimal(self.low_price)
        high_value = Decimal(self.high_price)
        open_value = Decimal(self.open_price)
        close_value = Decimal(self.close_price)

        if low_value > high_value:
            raise ValueError(
                "Historical candle low_price must be less than or equal to "
                "high_price."
            )

        if not low_value <= open_value <= high_value:
            raise ValueError(
                "Historical candle open_price must be within the inclusive "
                "low_price and high_price range."
            )

        if not low_value <= close_value <= high_value:
            raise ValueError(
                "Historical candle close_price must be within the inclusive "
                "low_price and high_price range."
            )


@dataclass(frozen=True, slots=True)
class DownloadResult:
    """Describe the immutable output of one historical download workflow.

    Purpose:
        Represent the canonical repository-wide result object returned after a
        historical candle download completes.

    Parameters:
        request: Immutable historical candle request that was executed.
        provider_id: Stable provider identifier used for the download.
        candles: Oldest-first canonical candle collection.
        returned_start_time_ms: Oldest returned candle timestamp, when candles
            are present.
        returned_end_time_ms: Newest returned candle timestamp, when candles
            are present.
        total_pages: Number of provider pages processed.
        total_requests: Number of runtime requests executed.
        execution_duration_seconds: Optional workflow execution duration.

    Attributes:
        request: Immutable historical candle request that was executed.
        provider_id: Stable provider identifier used for the download.
        candles: Oldest-first canonical candle collection.
        returned_start_time_ms: Oldest returned candle timestamp, when candles
            are present.
        returned_end_time_ms: Newest returned candle timestamp, when candles
            are present.
        total_pages: Number of provider pages processed.
        total_requests: Number of runtime requests executed.
        execution_duration_seconds: Optional workflow execution duration.

    Raises:
        ValueError: If result metadata is structurally invalid.
        TypeError: If result metadata uses unsupported types.

    Usage Notes:
        This object is immutable and does not own normalization or execution
        behavior.
    """

    request: HistoricalCandleRequest
    provider_id: str
    candles: tuple[HistoricalCandle, ...]
    returned_start_time_ms: int | None = None
    returned_end_time_ms: int | None = None
    total_pages: int = 0
    total_requests: int = 0
    execution_duration_seconds: float | None = None

    def __post_init__(self) -> None:
        """Validate result invariants."""
        if not isinstance(self.request, HistoricalCandleRequest):
            raise TypeError(
                "Download result request must be a HistoricalCandleRequest instance."
            )

        object.__setattr__(
            self,
            "provider_id",
            _normalize_identifier(self.provider_id, "provider_id"),
        )

        normalized_candles = _normalize_candles(
            candles=self.candles,
            request=self.request,
            provider_id=self.provider_id,
        )
        object.__setattr__(self, "candles", normalized_candles)

        object.__setattr__(
            self,
            "returned_start_time_ms",
            _normalize_timestamp(
                self.returned_start_time_ms,
                "returned_start_time_ms",
                allow_none=True,
            ),
        )
        object.__setattr__(
            self,
            "returned_end_time_ms",
            _normalize_timestamp(
                self.returned_end_time_ms,
                "returned_end_time_ms",
                allow_none=True,
            ),
        )
        object.__setattr__(
            self,
            "total_pages",
            _normalize_non_negative_int(self.total_pages, "total_pages"),
        )
        object.__setattr__(
            self,
            "total_requests",
            _normalize_non_negative_int(self.total_requests, "total_requests"),
        )
        object.__setattr__(
            self,
            "execution_duration_seconds",
            _normalize_duration(self.execution_duration_seconds),
        )

        if not self.candles:
            if (
                self.returned_start_time_ms is not None
                or self.returned_end_time_ms is not None
            ):
                raise ValueError(
                    "Download result returned interval metadata must be omitted "
                    "when candles are empty."
                )
            return

        if self.returned_start_time_ms is None or self.returned_end_time_ms is None:
            raise ValueError(
                "Download result returned interval metadata must be set when "
                "candles are present."
            )

        if self.returned_end_time_ms < self.returned_start_time_ms:
            raise ValueError(
                "Download result returned_end_time_ms must be greater than or "
                "equal to returned_start_time_ms."
            )

        first_candle_time = self.candles[0].open_time_ms
        last_candle_time = self.candles[-1].open_time_ms
        if self.returned_start_time_ms != first_candle_time:
            raise ValueError(
                "Download result returned_start_time_ms must match the first "
                "candle open_time_ms."
            )

        if self.returned_end_time_ms != last_candle_time:
            raise ValueError(
                "Download result returned_end_time_ms must match the last "
                "candle open_time_ms."
            )


def _normalize_identifier(value: str, field_name: str) -> str:
    """Normalize and validate a stable identifier string."""
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} must be non-empty.")

    return normalized_value


def _normalize_timestamp(
    value: int | None,
    field_name: str,
    *,
    allow_none: bool = False,
) -> int | None:
    """Normalize and validate a UTC epoch millisecond timestamp."""
    if value is None:
        if allow_none:
            return None
        raise TypeError(f"{field_name} must be an integer.")

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value < 0:
        raise ValueError(f"{field_name} must be greater than or equal to zero.")

    return value


def _normalize_positive_int(
    value: int | None,
    field_name: str,
    *,
    allow_none: bool = False,
) -> int | None:
    """Normalize and validate an optional positive integer."""
    if value is None:
        if allow_none:
            return None
        raise TypeError(f"{field_name} must be an integer.")

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")

    return value


def _normalize_non_negative_int(value: int, field_name: str) -> int:
    """Normalize and validate a non-negative integer."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value < 0:
        raise ValueError(f"{field_name} must be greater than or equal to zero.")

    return value


def _normalize_duration(value: float | None) -> float | None:
    """Normalize and validate an optional execution duration."""
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("execution_duration_seconds must be a float.")

    normalized_value = float(value)
    if normalized_value < 0:
        raise ValueError("execution_duration_seconds must be non-negative.")

    return normalized_value


def _normalize_decimal_text(
    value: str | None,
    field_name: str,
    *,
    allow_none: bool = False,
    allow_zero: bool = True,
) -> str | None:
    """Normalize a canonical decimal string while preserving textual precision."""
    if value is None:
        if allow_none:
            return None
        raise TypeError(f"{field_name} must be a string.")

    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string.")

    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} must be non-empty.")

    try:
        numeric_value = Decimal(normalized_value)
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} must be a valid decimal string.") from exc

    if numeric_value.is_nan() or numeric_value.is_infinite():
        raise ValueError(f"{field_name} must be a finite decimal string.")

    if numeric_value < 0:
        raise ValueError(f"{field_name} must be non-negative.")

    if not allow_zero and numeric_value == 0:
        raise ValueError(f"{field_name} must be greater than zero.")

    return normalized_value


def _normalize_candles(
    *,
    candles: tuple[HistoricalCandle, ...],
    request: HistoricalCandleRequest,
    provider_id: str,
) -> tuple[HistoricalCandle, ...]:
    """Normalize and validate the final candle collection."""
    if not isinstance(candles, tuple):
        raise TypeError("Download result candles must be a tuple.")

    previous_timestamp: int | None = None
    for candle in candles:
        if not isinstance(candle, HistoricalCandle):
            raise TypeError(
                "Download result candles must contain HistoricalCandle instances."
            )

        if candle.provider_id != provider_id:
            raise ValueError(
                "Download result candles must all use the result provider_id."
            )

        if candle.symbol != request.symbol:
            raise ValueError(
                "Download result candles must all use the request symbol."
            )

        if candle.timeframe != request.timeframe:
            raise ValueError(
                "Download result candles must all use the request timeframe."
            )

        if previous_timestamp is not None and candle.open_time_ms < previous_timestamp:
            raise ValueError(
                "Download result candles must be ordered from oldest to newest."
            )

        previous_timestamp = candle.open_time_ms

    return candles
