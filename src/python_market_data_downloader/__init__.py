"""Top-level package for python-market-data-downloader."""

from __future__ import annotations

from python_market_data_downloader import downloader as _downloader
from python_market_data_downloader import models as _models
from python_market_data_downloader import provider as _provider

MarketDataDownloader = _downloader.MarketDataDownloader
HistoricalCandleRequest = _models.HistoricalCandleRequest
HistoricalCandle = _models.HistoricalCandle
DownloadResult = _models.DownloadResult
MarketDataProvider = _provider.MarketDataProvider

__all__ = [
    "DownloadResult",
    "HistoricalCandle",
    "HistoricalCandleRequest",
    "MarketDataDownloader",
    "MarketDataProvider",
]
