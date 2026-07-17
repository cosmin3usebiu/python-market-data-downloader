# R004 Decisions: python-market-data-downloader

## Status

This is a recovered draft proposal based on observed implementation evidence.
It does not approve or freeze R004.

R004 approval/freeze state remains unverified. The API is not frozen. Release Phase is not assigned.

All decisions in this file are proposed and unapproved unless explicitly stated
otherwise.

## Decisions To Ratify

### DEC-R004-001: R004 Owns Historical Market-Data Download Orchestration

Decision to ratify:

R004 owns bounded historical candle download orchestration above the exchange
integration runtime.

Evidence:

Observed `MarketDataDownloader`, `HistoricalCandleRequest`, planning, provider
invocation, runtime execution, and canonical `DownloadResult`.

Status:

Proposed, not approved.

### DEC-R004-002: R004 Depends On R003 For Exchange Runtime Execution

Decision to ratify:

R004 must delegate exchange request execution to
`python-exchange-integration-runtime`.

Evidence:

Observed source imports and uses `ExchangeRuntime`, `ExchangeRequest`, and
`ExchangeResponse`.

Status:

Proposed, not approved.

### DEC-R004-003: R004 Declares R001 But Does Not Own Configuration Loading

Decision to ratify:

R004 may depend on configuration infrastructure, but it must not implement its
own configuration loading.

Evidence:

`pyproject.toml` declares `python-configuration-system`; observed source does
not show configuration loading behavior.

Status:

Proposed, not approved.

### DEC-R004-004: MarketDataProvider Owns Provider-Specific Request And Parse Behavior

Decision to ratify:

Providers own provider-specific request construction and response parsing, while
downloader orchestration and normalization remain in R004 core.

Evidence:

Observed `MarketDataProvider.build_exchange_request()` and
`MarketDataProvider.parse_page()` contracts.

Status:

Proposed, not approved.

### DEC-R004-005: Planning Remains Deterministic And Internal

Decision to ratify:

Download planning should remain deterministic, side-effect free, and internal to
R004.

Evidence:

Observed `_DownloadPlan`, `_DownloadWindow`, `_build_download_plan()`,
`_get_next_window()`, and `_is_plan_complete()`.

Status:

Proposed, not approved.

### DEC-R004-006: Normalization Owns Canonical Candle Assembly

Decision to ratify:

Normalization owns canonical candle construction, chronological ordering,
duplicate handling, interval enforcement, and final result assembly.

Evidence:

Observed `_normalize_collected_download()`, `_collect_canonical_candles()`, and
`_deduplicate_candles()`.

Status:

Proposed, not approved.

### DEC-R004-007: Public API Remains Minimal

Decision to ratify:

Package-root public API should remain limited to core request, result, provider,
and downloader concepts unless expansion is explicitly approved.

Evidence:

Observed `__all__` exports exactly five objects.

Status:

Proposed, not approved.

### DEC-R004-008: R004 Does Not Own Persistence Or Dataset Output

Decision to ratify:

R004 returns canonical download results and must not own dataset persistence,
CSV output, database storage, or file layout behavior.

Evidence:

Observed implementation returns `DownloadResult`; no persistence modules are
observed.

Status:

Proposed, not approved.

## Open Decisions

- Whether repository-native downloader error classes should become package-root
  public API.
- Whether internal provider page/record artifacts should remain internal.
- Whether concrete market-data providers belong in R004 or
  downstream/provider-specific repositories.
- Whether `python-configuration-system` should remain a declared runtime
  dependency if source usage is not observed.
- Whether `summary.py` should remain placeholder, be documented, or be removed
  during a future approved release/recovery work package.
- Whether R004 should enter Release Phase after artifact recovery or require
  additional code review.
- Whether CI dependency installation risk should be addressed before release
  recovery.

## Evidence Limitations

Source and tests provide implementation evidence. They do not prove prior
approval, API freeze, milestone approval, or release readiness.

README, documentation, examples, and changelog are stale and should not be
treated as authoritative where they conflict with source/tests.

This file does not approve R004, freeze R004, freeze the API, assign Release
Phase, approve milestones, or declare release readiness.
