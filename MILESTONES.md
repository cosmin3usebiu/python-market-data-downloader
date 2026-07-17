# R004 Milestones: python-market-data-downloader

## Status

This is a recovered draft proposal based on observed implementation evidence.
It does not approve or freeze R004.

R004 approval/freeze state remains unverified. The API is not frozen. Release Phase is not assigned.

Milestone approval is not granted by this file. Observed code and tests are
evidence only.

No milestone is approved or frozen by this file.

## Proposed Milestone 1: Repository Skeleton

Observed evidence:

- Packaging metadata.
- CI workflow.
- Source package layout.
- Test package layout.
- Documentation and example directories.
- `py.typed`.

Acceptance criteria:

- Repository structure exists.
- Package is importable.
- No downloader behavior required.

Status:

- Appears implemented based on observed files.
- Not approved.

## Proposed Milestone 2: Public Models And Exception Hierarchy

Observed evidence:

- `HistoricalCandleRequest`
- `HistoricalCandle`
- `DownloadResult`
- Repository-native exception hierarchy.
- Model and exception tests.

Acceptance criteria:

- Immutable public models.
- Local structural validation.
- Canonical candle precision preserved as strings.
- Repository-native root exception exists.
- No orchestration required.

Status:

- Appears implemented based on observed source/tests.
- Not approved.

## Proposed Milestone 3: Provider Contract

Observed evidence:

- `MarketDataProvider`
- `_ProviderCandleRecord`
- `_ProviderPage`
- Provider contract tests.

Acceptance criteria:

- Provider id validation.
- Provider request construction contract.
- Provider page parsing contract.
- Provider-native immutable record/page artifacts.
- No final canonical normalization responsibility in providers.

Status:

- Appears implemented based on observed source/tests.
- Not approved.

## Proposed Milestone 4: Planning And Download Plan

Observed evidence:

- `_DownloadWindow`
- `_DownloadPlan`
- `_build_download_plan`
- `_get_next_window`
- `_is_plan_complete`
- Planning tests.

Acceptance criteria:

- Deterministic window construction.
- Timeframe parsing.
- Page-size-based interval slicing.
- Max-request validation.
- Plan completion checks.
- Internal-only planning artifacts.

Status:

- Appears implemented based on observed source/tests.
- Not approved.

## Proposed Milestone 5: Downloader Orchestration

Observed evidence:

- `MarketDataDownloader`
- `_CollectedPage`
- `_CollectedDownload`
- Downloader orchestration tests.

Acceptance criteria:

- Downloader validates collaborators.
- Downloader validates request input.
- Downloader builds plans.
- Downloader invokes provider request construction.
- Downloader delegates execution to R003 `ExchangeRuntime`.
- Downloader invokes provider page parsing.
- Downloader handles provider pagination tokens.
- Downloader rejects unprogressable or repeated pagination tokens.

Status:

- Appears implemented based on observed source/tests.
- Not approved.

## Proposed Milestone 6: Normalization And Result Assembly

Observed evidence:

- `_normalize_collected_download`
- `_collect_canonical_candles`
- `_deduplicate_candles`
- Download result tests.

Acceptance criteria:

- Provider records normalize into canonical `HistoricalCandle` objects.
- Candles are ordered oldest-first.
- Duplicate identical timestamps are deduplicated.
- Conflicting duplicate timestamps fail.
- Records outside request interval fail.
- Empty collections are supported.
- Final `DownloadResult` is structurally valid.

Status:

- Appears implemented based on observed source/tests.
- Not approved.

## Proposed Milestone 7: Error Normalization And Behavioral Completion

Observed evidence:

- Repository-native error classes.
- Tests for planning, provider, runtime, and normalization failures.

Acceptance criteria:

- Planning failures surface as `DownloadPlanningError`.
- Provider request construction failures surface as `ProviderConfigurationError`.
- Provider page parsing failures surface as `ProviderConfigurationError`.
- Exchange runtime execution failures surface as `DownloadExecutionError`.
- Normalization failures surface as `NormalizationError`.
- Original exception context is preserved where unexpected failures are
  normalized.

Status:

- Appears implemented based on observed source/tests.
- Not approved.

## Proposed Milestone 8: Documentation And Release Recovery

Observed evidence:

- README says repository is still Milestone 1.
- Documentation and examples are placeholder-level.
- CHANGELOG records only initial skeleton.
- `summary.py` remains placeholder-only.

Acceptance criteria:

- README reflects observed implementation.
- Architecture docs describe provider, planning, orchestration, normalization,
  and dependency boundaries.
- API documentation reflects approved API after review.
- Examples use approved public API only.
- Changelog and release notes align with approved scope.
- Summary placeholder status is reviewed.

Status:

- Incomplete.
- Not approved.

## Recovery Status

Proposed milestones 1-7 appear implemented based on observed source/tests but
are not approved.

Proposed milestone 8 is incomplete because documentation, examples, changelog,
and summary behavior remain stale or placeholder-level.

No milestone is approved or frozen by this file.

No concrete provider, persistence, storage, live exchange, CLI, indicator,
trading, or strategy milestone is approved by this file.
