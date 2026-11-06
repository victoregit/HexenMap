"""Performance monitoring, latency profiling, percentile stats, and resource tracking."""

from __future__ import annotations
from collections import defaultdict
import logging
import os
import time
from typing import Any, Dict, List, Optional

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)


class MetricStats:
    """Statistical summary for recorded metrics."""

    def __init__(self, values: List[float]) -> None:
        self.count = len(values)
        if self.count == 0:
            self.min = 0.0
            self.max = 0.0
            self.mean = 0.0
            self.p50 = 0.0
            self.p95 = 0.0
            self.p99 = 0.0
            return

        sorted_vals = sorted(values)
        self.min = float(sorted_vals[0])
        self.max = float(sorted_vals[-1])
        self.mean = float(sum(sorted_vals) / self.count)
        self.p50 = self._percentile(sorted_vals, 50)
        self.p95 = self._percentile(sorted_vals, 95)
        self.p99 = self._percentile(sorted_vals, 99)

    @staticmethod
    def _percentile(sorted_vals: List[float], pct: float) -> float:
        n = len(sorted_vals)
        if n == 1:
            return float(sorted_vals[0])
        idx = (pct / 100.0) * (n - 1)
        low = int(idx)
        high = min(low + 1, n - 1)
        weight = idx - low
        return float(sorted_vals[low] * (1.0 - weight) + sorted_vals[high] * weight)

    def to_dict(self) -> Dict[str, float]:
        return {
            "count": self.count,
            "min": round(self.min, 3),
            "mean": round(self.mean, 3),
            "max": round(self.max, 3),
            "p50": round(self.p50, 3),
            "p95": round(self.p95, 3),
            "p99": round(self.p99, 3),
        }


class PerformanceMonitor:
    """Tracks latency metrics (p50, p95, p99) and system resource utilization."""

    def __init__(self, max_samples_per_category: int = 10000) -> None:
        self._samples: Dict[str, List[float]] = defaultdict(list)
        self._max_samples = max_samples_per_category
        self._process = psutil.Process(os.getpid()) if psutil else None
        self._start_time = time.time()

    def record_metric(self, category: str, value_ms: float) -> None:
        """Record a single latency or numerical observation."""
        cat_samples = self._samples[category]
        if len(cat_samples) >= self._max_samples:
            cat_samples.pop(0)
        cat_samples.append(float(value_ms))

    def record_render_time(self, ms: float) -> None:
        """Record map rendering cycle latency in milliseconds."""
        self.record_metric("render_ms", ms)

    def record_cv_time(self, ms: float) -> None:
        """Record computer vision inference/matching latency in milliseconds."""
        self.record_metric("cv_ms", ms)

    def record_query_time(self, ms: float) -> None:
        """Record marker repository spatial/filter query latency in milliseconds."""
        self.record_metric("query_ms", ms)

    def get_stats(self, category: str) -> MetricStats:
        """Retrieve computed statistical metrics for category."""
        return MetricStats(self._samples.get(category, []))

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Return dict of all category metric stats."""
        return {cat: self.get_stats(cat).to_dict() for cat in self._samples}

    def get_system_resources(self) -> Dict[str, float]:
        """Fetch current process CPU percentage and RAM usage."""
        cpu_pct = 0.0
        ram_rss_mb = 0.0

        if self._process and psutil:
            try:
                # cpu_percent on Process
                cpu_pct = float(self._process.cpu_percent(interval=None))
                mem_info = self._process.memory_info()
                ram_rss_mb = float(mem_info.rss / (1024 * 1024))
            except Exception as e:
                logger.debug("psutil error retrieving metrics: %s", e)

        return {
            "cpu_percent": round(cpu_pct, 2),
            "ram_rss_mb": round(ram_rss_mb, 2),
            "uptime_sec": round(time.time() - self._start_time, 2),
        }

    def reset(self) -> None:
        """Clear all stored latency samples."""
        self._samples.clear()
        self._start_time = time.time()

    def generate_summary_table(self) -> str:
        """Generate a human-readable text summary of all recorded metrics."""
        sys_res = self.get_system_resources()
        lines = [
            "=" * 68,
            "                   PERFORMANCE MONITOR SUMMARY                   ",
            "=" * 68,
            f"Process Memory (RSS): {sys_res['ram_rss_mb']} MB | CPU: {sys_res['cpu_percent']}% | Uptime: {sys_res['uptime_sec']}s",
            "-" * 68,
            f"{'Metric':<16} {'Count':<8} {'Mean(ms)':<10} {'p50(ms)':<9} {'p95(ms)':<9} {'p99(ms)':<9}",
            "-" * 68,
        ]

        for cat, samples in sorted(self._samples.items()):
            s = MetricStats(samples)
            lines.append(
                f"{cat:<16} {s.count:<8} {s.mean:<10.3f} {s.p50:<9.3f} {s.p95:<9.3f} {s.p99:<9.3f}"
            )

        lines.append("=" * 68)
        return "\n".join(lines)
