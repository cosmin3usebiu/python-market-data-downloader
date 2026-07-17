"""Market-data provider contract definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from python_exchange_integration_runtime import ExchangeRequest, ExchangeResponse

from python_market_data_downloader.errors import ProviderConfigurationError
from python_market_data_downloader.models import HistoricalCandleRequest


class MarketDataProvider(ABC):
    """Define the public provider contract for exchange-specific data access.

    Purpose:
        Isolate exchange-specific candle request construction and exchange
        response parsing behind one stable repository-level contract.

    Parameters:
        provider_id: Stable provider identifier used across requests and
            download results.

    Attributes:
        provider_id: Stable provider identifier used across requests and
            download results.

    Raises:
        ProviderConfigurationError: If provider construction metadata is
            invalid.

    Usage Notes:
        Providers should remain stateless, or behave as if stateless, across
        requests. Providers do not own planning, orchestration, normalization,
        or final result assembly.
    """

    def __init__(self, *, provider_id: str) -> None:
        """Normalize and validate provider identity."""
        self._provider_id = _normalize_provider_id(provider_id)

    @property
    def provider_id(self) -> str:
        """Return the stable provider identifier."""
        return self._provider_id

    @abstractmethod
    def build_exchange_request(
        self,
        request: HistoricalCandleRequest,
        *,
        start_time_ms: int,
        end_time_ms: int,
        page_size: int | None = None,
        page_token: str | None = None,
    ) -> ExchangeRequest:
        """Build one exchange request for a bounded historical page.

        Args:
            request: Canonical historical candle download request.
            start_time_ms: Inclusive page start timestamp in UTC epoch
                milliseconds.
            end_time_ms: Exclusive page end timestamp in UTC epoch
                milliseconds.
            page_size: Optional provider page-size override for this page.
            page_token: Optional provider-specific pagination token.

        Returns:
            An immutable exchange request ready for execution through
            ``python-exchange-integration-runtime``.

        Raises:
            ProviderConfigurationError: If the provider cannot construct a
                valid request for the supplied boundaries.
        """

    @abstractmethod
    def parse_page(
        self,
        request: HistoricalCandleRequest,
        response: ExchangeResponse,
    ) -> _ProviderPage:
        """Parse one exchange response into provider-native logical records.

        Args:
            request: Canonical historical candle download request.
            response: Exchange response returned by the exchange runtime.

        Returns:
            One immutable provider page containing logical records and
            provider-specific pagination state.

        Raises:
            ProviderConfigurationError: If the response cannot be parsed into a
                structurally valid provider page.
        """


@dataclass(frozen=True, slots=True)
class _ProviderCandleRecord:
    """Describe one exchange-native logical candle record.

    Purpose:
        Provide an immutable intermediate record returned by providers before
        repository-wide canonical normalization is applied.

    Parameters:
        open_time_ms: UTC epoch millisecond open timestamp.
        open_price: Exchange-native open price string.
        high_price: Exchange-native high price string.
        low_price: Exchange-native low price string.
        close_price: Exchange-native close price string.
        volume: Optional exchange-native volume string.

    Attributes:
        open_time_ms: UTC epoch millisecond open timestamp.
        open_price: Exchange-native open price string.
        high_price: Exchange-native high price string.
        low_price: Exchange-native low price string.
        close_price: Exchange-native close price string.
        volume: Optional exchange-native volume string.

    Raises:
        ValueError: If the record is structurally invalid.
        TypeError: If the record uses unsupported types.

    Usage Notes:
        This type is internal to the provider contract and is not exported from
        the package root.
    """

    open_time_ms: int
    open_price: str
    high_price: str
    low_price: str
    close_price: str
    volume: str | None = None

    def __post_init__(self) -> None:
        """Validate provider-native record invariants."""
        object.__setattr__(
            self,
            "open_time_ms",
            _normalize_timestamp(self.open_time_ms, "open_time_ms"),
        )

        open_price = _normalize_decimal_text(self.open_price, "open_price")
        high_price = _normalize_decimal_text(self.high_price, "high_price")
        low_price = _normalize_decimal_text(self.low_price, "low_price")
        close_price = _normalize_decimal_text(self.close_price, "close_price")
        volume = _normalize_decimal_text(
            self.volume,
            "volume",
            allow_none=True,
        )

        object.__setattr__(self, "open_price", open_price)
        object.__setattr__(self, "high_price", high_price)
        object.__setattr__(self, "low_price", low_price)
        object.__setattr__(self, "close_price", close_price)
        object.__setattr__(self, "volume", volume)

        low_value = Decimal(self.low_price)
        high_value = Decimal(self.high_price)
        open_value = Decimal(self.open_price)
        close_value = Decimal(self.close_price)

        if low_value > high_value:
            raise ValueError(
                "Provider candle record low_price must be less than or equal "
                "to high_price."
            )

        if not low_value <= open_value <= high_value:
            raise ValueError(
                "Provider candle record open_price must be within the "
                "inclusive low_price and high_price range."
            )

        if not low_value <= close_value <= high_value:
            raise ValueError(
                "Provider candle record close_price must be within the "
                "inclusive low_price and high_price range."
            )


@dataclass(frozen=True, slots=True)
class _ProviderPage:
    """Describe one provider-native parsed response page.

    Purpose:
        Provide an immutable intermediate page artifact containing logical
        candle records and pagination state before canonical repository
        normalization and result assembly occur.

    Parameters:
        records: Provider-native logical records for one page.
        next_page_token: Optional provider-specific pagination token.
        is_complete: Whether the provider declares the page sequence complete.

    Attributes:
        records: Provider-native logical records for one page.
        next_page_token: Optional provider-specific pagination token.
        is_complete: Whether the provider declares the page sequence complete.

    Raises:
        ValueError: If page metadata is structurally invalid.
        TypeError: If page metadata uses unsupported types.

    Usage Notes:
        This type is internal to the provider contract and is not exported from
        the package root.
    """

    records: tuple[_ProviderCandleRecord, ...]
    next_page_token: str | None = None
    is_complete: bool = False

    def __post_init__(self) -> None:
        """Validate provider page invariants."""
        object.__setattr__(self, "records", _normalize_records(self.records))
        object.__setattr__(
            self,
            "next_page_token",
            _normalize_optional_token(self.next_page_token),
        )

        if not isinstance(self.is_complete, bool):
            raise TypeError("Provider page is_complete must be a boolean.")

        if self.is_complete and self.next_page_token is not None:
            raise ValueError(
                "Provider page next_page_token must be omitted when "
                "is_complete is True."
            )


def _normalize_provider_id(provider_id: str) -> str:
    """Normalize and validate a stable provider identifier."""
    if not isinstance(provider_id, str):
        raise ProviderConfigurationError("Provider id must be a string.")

    normalized_provider_id = provider_id.strip()
    if not normalized_provider_id:
        raise ProviderConfigurationError("Provider id must be non-empty.")

    return normalized_provider_id


def _normalize_timestamp(value: int, field_name: str) -> int:
    """Normalize and validate a UTC epoch millisecond timestamp."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer.")

    if value < 0:
        raise ValueError(f"{field_name} must be greater than or equal to zero.")

    return value


def _normalize_decimal_text(
    value: str | None,
    field_name: str,
    *,
    allow_none: bool = False,
) -> str | None:
    """Normalize and validate provider-native decimal strings."""
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

    return normalized_value


def _normalize_records(
    records: tuple[_ProviderCandleRecord, ...],
) -> tuple[_ProviderCandleRecord, ...]:
    """Normalize and validate provider record collections."""
    if not isinstance(records, tuple):
        raise TypeError("Provider page records must be a tuple.")

    for record in records:
        if not isinstance(record, _ProviderCandleRecord):
            raise TypeError(
                "Provider page records must contain _ProviderCandleRecord instances."
            )

    return records


def _normalize_optional_token(value: str | None) -> str | None:
    """Normalize and validate an optional provider pagination token."""
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError("Provider page next_page_token must be a string.")

    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError("Provider page next_page_token must be non-empty.")

    return normalized_value
