"""Repository exception hierarchy for market-data downloader failures.

This module defines the repository-native exception categories used across
planning, provider collaboration, download orchestration, and normalization
boundaries.
"""

from __future__ import annotations


class MarketDataDownloaderError(Exception):
    """Base exception for repository-level market-data downloader failures.

    Purpose:
        Provide a stable root exception type so callers can catch repository
        failures without depending on lower-level implementation details.

    Parameters:
        This exception accepts the standard ``Exception`` initialization
        arguments only.

    Attributes:
        No additional public attributes are defined.

    Raises:
        This class serves as the repository root exception and is not intended
        to represent a specific operational category by itself.

    Usage Notes:
        More specific planning, provider, execution, and normalization
        failures derive from this base type.
    """


class ProviderConfigurationError(MarketDataDownloaderError):
    """Describe invalid provider configuration or provider contract state.

    Purpose:
        Signal that a market-data provider is structurally invalid or violates
        the repository's provider-level configuration expectations.

    Parameters:
        This exception accepts the standard ``Exception`` initialization
        arguments only.

    Attributes:
        No additional public attributes are defined.

    Raises:
        This exception will later be used when provider registration or
        provider contract validation detects invalid configuration state.

    Usage Notes:
        Provider configuration failures are distinct from execution and
        normalization failures.
    """


class DownloadPlanningError(MarketDataDownloaderError):
    """Describe failures in deterministic download planning.

    Purpose:
        Represent invalid or unsatisfiable planning conditions such as
        unsupported intervals, impossible pagination windows, or structurally
        invalid plan inputs.

    Parameters:
        This exception accepts the standard ``Exception`` initialization
        arguments only.

    Attributes:
        No additional public attributes are defined.

    Raises:
        This exception will later be used when request planning or internal
        plan generation fails.

    Usage Notes:
        Planning failures are intentionally separate from execution-time
        provider or runtime failures.
    """


class DownloadExecutionError(MarketDataDownloaderError):
    """Describe failures while executing a planned download workflow.

    Purpose:
        Normalize failures that occur while orchestrating provider calls or
        lower-layer runtime execution after a plan has been created.

    Parameters:
        This exception accepts the standard ``Exception`` initialization
        arguments only.

    Attributes:
        No additional public attributes are defined.

    Raises:
        This exception will later be used when request execution or workflow
        orchestration crosses an invalid operational boundary.

    Usage Notes:
        Execution failures are distinct from planning and normalization
        failures because they occur after orchestration has begun.
    """


class NormalizationError(MarketDataDownloaderError):
    """Describe failures while canonicalizing provider-returned records.

    Purpose:
        Represent invalid record structure, invalid canonical values, or other
        failures encountered while converting exchange-native records into
        repository-wide candle objects.

    Parameters:
        This exception accepts the standard ``Exception`` initialization
        arguments only.

    Attributes:
        No additional public attributes are defined.

    Raises:
        This exception will later be used when normalization or result assembly
        detects invalid market-data record state.

    Usage Notes:
        Normalization failures should remain separate from provider and
        execution failures because they apply to canonical repository output.
    """
