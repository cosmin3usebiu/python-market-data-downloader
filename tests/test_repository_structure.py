"""Smoke tests for the repository skeleton."""

from __future__ import annotations

import importlib


def test_package_imports() -> None:
    """Verify the package is importable."""
    module = importlib.import_module("python_market_data_downloader")

    assert module is not None


def test_package_root_exports_no_public_api_yet() -> None:
    """Verify the package root exposes only approved milestone-two models."""
    module = importlib.import_module("python_market_data_downloader")

    assert hasattr(module, "__all__")
    assert module.__all__ == [
        "DownloadResult",
        "HistoricalCandle",
        "HistoricalCandleRequest",
        "MarketDataDownloader",
        "MarketDataProvider",
    ]


def test_internal_placeholder_modules_import() -> None:
    """Verify internal placeholder modules are importable."""
    module_names = (
        "python_market_data_downloader.download_plan",
        "python_market_data_downloader.downloader",
        "python_market_data_downloader.errors",
        "python_market_data_downloader.models",
        "python_market_data_downloader.normalization",
        "python_market_data_downloader.planning",
        "python_market_data_downloader.provider",
        "python_market_data_downloader.summary",
    )

    for module_name in module_names:
        assert importlib.import_module(module_name) is not None
