# R004 API: python-market-data-downloader

## Status

This is a recovered draft proposal based on observed implementation evidence.
It does not approve or freeze R004.

R004 approval/freeze state remains unverified. The API is not frozen. Release Phase is not assigned.

Current `__all__` is observed implementation evidence, not a frozen public
contract.

Any future API freeze requires explicit review and approval.

## Observed Public Exports

Package-root `__all__` exports:

- `DownloadResult`
- `HistoricalCandle`
- `HistoricalCandleRequest`
- `MarketDataDownloader`
- `MarketDataProvider`

## Proposed Classification: Core Public API

- `DownloadResult`
- `HistoricalCandle`
- `HistoricalCandleRequest`
- `MarketDataDownloader`
- `MarketDataProvider`

## Proposed Classification: Public But Requires Review

- `MarketDataDownloaderError`
- `ProviderConfigurationError`
- `DownloadPlanningError`
- `DownloadExecutionError`
- `NormalizationError`

## Proposed Classification: Internal Implementation Candidates

- `_ProviderCandleRecord`
- `_ProviderPage`
- `_DownloadWindow`
- `_DownloadPlan`
- `_CollectedPage`
- `_CollectedDownload`
- `_build_download_plan`
- `_get_next_window`
- `_is_plan_complete`
- `_normalize_collected_download`
- `_collect_canonical_candles`
- `_deduplicate_candles`
- model normalization helpers
- provider normalization helpers
- planning helper functions
- `summary.py`

## Known API Caveats

Repository-native error classes are implemented but are not package-root
exports.

Internal provider, planning, collected-download, and normalization artifacts are
not package-root exports.

No concrete market-data provider is exported.

No persistence, storage, dataset, CLI, indicator, trading, strategy, order,
account, balance, position, or portfolio model is exported.

The API is not frozen.

## API Freeze Status

The API is not frozen.

This file does not approve R004, freeze R004, assign Release Phase, approve any
milestone, or declare release readiness.
