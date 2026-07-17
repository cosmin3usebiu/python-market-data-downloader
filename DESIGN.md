# R004 Design: python-market-data-downloader

## Status

This is a recovered draft proposal based on observed implementation evidence.
It does not approve or freeze R004.

R004 approval/freeze state remains unverified. The API is not frozen. Release Phase is not assigned.

This design is not yet approved.

## Purpose

R004 provides reusable historical market-data download orchestration.

R004 coordinates bounded historical candle download workflows using provider
contracts and the upstream exchange integration runtime.

The repository answers:

How do I acquire canonical historical candle data through the platform stack?

## Scope

R004 owns:

- Historical candle download request modeling.
- Canonical historical candle modeling.
- Download result modeling.
- Market-data provider contract.
- Deterministic download planning.
- Page-window construction.
- Provider pagination orchestration.
- Download execution orchestration.
- Canonical candle normalization.
- Duplicate candle timestamp handling.
- Repository-native downloader exceptions.

## Non-Goals

R004 does not own:

- Configuration loading.
- HTTP request execution.
- HTTP transport implementations.
- Exchange adapter implementation.
- Exchange request signing.
- Exchange endpoint catalogs.
- Concrete market-data providers.
- Dataset persistence.
- CSV writing.
- Database storage.
- Caching.
- WebSocket streaming.
- Live polling loops.
- Indicator calculation.
- Trading logic.
- Strategy logic.
- Portfolio logic.
- Order, account, balance, position, or trade models.

## Architecture Boundaries

Public model layer:

- `models.py`

Public provider contract:

- `provider.py`

Internal planning layer:

- `download_plan.py`
- `planning.py`

Orchestration layer:

- `downloader.py`

Normalization layer:

- `normalization.py`

Error layer:

- `errors.py`

Deferred summary layer:

- `summary.py`

## Dependency Policy

R004 declares dependencies on:

- `python-configuration-system`
- `python-exchange-integration-runtime`

R004 source currently shows operational use of
`python-exchange-integration-runtime`.

R004 source usage of `python-configuration-system` is not evident from observed
source and requires future review.

R004 must use R003 for exchange runtime execution.

R004 must not bypass the exchange integration runtime.

R004 must not implement HTTP execution, exchange signing, or exchange adapter
behavior.

R004 must remain independent of downstream repositories such as dataset
pipelines, indicator engines, trading systems, or applications.

## Public / Private Module Boundary

The observed package-root public API is:

- `DownloadResult`
- `HistoricalCandle`
- `HistoricalCandleRequest`
- `MarketDataDownloader`
- `MarketDataProvider`

Repository-native downloader errors are observed implementation components and
require explicit review before any public API freeze.

Internal provider, planning, collected-download, and normalization artifacts
require explicit review before any public API freeze.

## Downloader Orchestration Model

`MarketDataDownloader` coordinates:

1. `HistoricalCandleRequest`
2. deterministic planning
3. provider exchange request construction
4. R003 exchange runtime execution
5. provider page parsing
6. pagination progression
7. collected raw pages
8. canonical normalization
9. `DownloadResult`

The downloader owns orchestration only.

## Provider Boundary

`MarketDataProvider` owns provider-specific request construction and response
parsing.

Providers return provider-native page artifacts. Providers do not own planning,
final canonical normalization, dataset persistence, or orchestration.

No concrete market-data provider is approved by this design.

## Planning And Pagination Boundary

Planning owns deterministic window construction from:

- request interval
- timeframe
- page size
- max request limit

Pagination owns provider page-token progression within a planned window.

R004 rejects unprogressable pagination and repeated page tokens.

## Normalization Boundary

Normalization owns:

- converting provider-native records into `HistoricalCandle`
- chronological ordering
- duplicate timestamp resolution
- conflicting duplicate rejection
- interval-boundary enforcement
- final `DownloadResult` assembly

Prices and volume remain strings to preserve precision.

## Configuration Boundary

R004 declares `python-configuration-system` as a dependency, but observed source
does not show configuration usage.

R004 must not implement its own configuration loading. Any configuration
integration requires explicit review.

## Exchange-Integration Boundary

R004 uses R003 exchange integration runtime concepts:

- `ExchangeRuntime`
- `ExchangeRequest`
- `ExchangeResponse`

R004 must not implement R003 responsibilities such as endpoint ownership,
adapter behavior, request signing, or exchange protocol abstraction.

## Validation And Error-Handling Expectations

R004 should fail fast on invalid request models, invalid provider outputs,
invalid plans, invalid pagination state, invalid exchange runtime outputs, and
invalid normalization artifacts.

Repository-native exceptions should preserve original exception context when
normalizing unexpected failures.

## Known Incomplete Or Deferred Capabilities

Observed deferred or absent capabilities:

- no concrete market-data provider
- no live exchange integration example
- no dataset persistence
- no CLI
- no caching
- no streaming or WebSocket support
- no summary implementation beyond placeholder text
- stale README, documentation, examples, and changelog
- clean CI dependency-resolution risk if upstream dependencies are not resolvable
- declared configuration dependency requires future review because usage is not
  evident from observed source

`summary.py` is placeholder-only and requires future review.

## Evidence Limitations

This design is recovered from observed source, tests, metadata, and stale
documentation.

Source and tests are implementation evidence, not approval evidence.

This document does not approve R004, freeze R004, freeze the API, assign Release
Phase, approve milestones, or declare release readiness.
