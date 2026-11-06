"""Unit tests for PerformanceMonitor latency metrics and resource measurements."""

import pytest
from src.performance.performance_monitor import MetricStats, PerformanceMonitor


class TestMetricStats:
    def test_empty_metrics(self):
        s = MetricStats([])
        assert s.count == 0
        assert s.mean == 0.0
        assert s.p50 == 0.0
        assert s.p95 == 0.0

    def test_percentile_calculations(self):
        # 100 values from 1 to 100
        values = list(range(1, 101))
        s = MetricStats(values)
        assert s.count == 100
        assert s.min == 1.0
        assert s.max == 100.0
        assert s.mean == 50.5
        assert pytest.approx(s.p50, 0.5) == 50.5
        assert pytest.approx(s.p95, 0.5) == 95.0
        assert pytest.approx(s.p99, 0.5) == 99.0


class TestPerformanceMonitor:
    def test_record_and_retrieve_metrics(self, perf_monitor):
        perf_monitor.record_render_time(12.5)
        perf_monitor.record_render_time(15.0)
        perf_monitor.record_render_time(10.0)

        perf_monitor.record_cv_time(25.0)
        perf_monitor.record_query_time(1.2)

        r_stats = perf_monitor.get_stats("render_ms")
        assert r_stats.count == 3
        assert r_stats.min == 10.0
        assert r_stats.max == 15.0
        assert pytest.approx(r_stats.mean, 0.01) == 12.5

        all_stats = perf_monitor.get_all_stats()
        assert "render_ms" in all_stats
        assert "cv_ms" in all_stats
        assert "query_ms" in all_stats

    def test_system_resources_and_summary(self, perf_monitor):
        res = perf_monitor.get_system_resources()
        assert "cpu_percent" in res
        assert "ram_rss_mb" in res
        assert res["ram_rss_mb"] > 0

        perf_monitor.record_render_time(5.5)
        table = perf_monitor.generate_summary_table()
        assert "PERFORMANCE MONITOR SUMMARY" in table
        assert "render_ms" in table
        assert "ram_rss_mb" in table or "Process Memory" in table

    def test_reset(self, perf_monitor):
        perf_monitor.record_render_time(5.5)
        assert perf_monitor.get_stats("render_ms").count == 1
        perf_monitor.reset()
        assert perf_monitor.get_stats("render_ms").count == 0
