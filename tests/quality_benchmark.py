import os
import threading
import time
import tracemalloc
from pathlib import Path

import psutil

from src.cleansheet.quality.quality_checker import check_quality


class SystemResourceMonitor:
    """Monitors OS-level process RAM and CPU in the background at fixed intervals."""

    def __init__(self, interval_sec: float = 0.05):
        self.interval = interval_sec
        self.process = psutil.Process(os.getpid())
        self._stop_event = threading.Event()
        self._monitor_thread = None

        self.peak_rss_bytes = 0
        self.start_rss_bytes = 0
        self.cpu_samples = []

    def start(self):
        # Warm-up CPU baseline and record initial RAM
        self.process.cpu_percent(interval=None)
        self.start_rss_bytes = self.process.memory_info().rss
        self.peak_rss_bytes = self.start_rss_bytes

        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._poll_resources, daemon=True)
        self._monitor_thread.start()

    def _poll_resources(self):
        while not self._stop_event.is_set():
            try:
                mem_info = self.process.memory_info()
                self.peak_rss_bytes = max(self.peak_rss_bytes, mem_info.rss)

                cpu = self.process.cpu_percent(interval=None)
                if cpu > 0.0:
                    self.cpu_samples.append(cpu)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

            time.sleep(self.interval)

    def stop(self):
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join()


def run_benchmark(filepath_str: str) -> None:
    filepath = Path(filepath_str).resolve()

    if not filepath.exists():
        print(f"Error: File not found -> {filepath}")
        return

    file_size_mb = filepath.stat().st_size / (1024 * 1024)
    print("=" * 60)
    print(f"BENCHMARKING: {filepath.name}")
    print(f"File Size:    {file_size_mb:.2f} MB")
    print("=" * 60)

    # 1. Prepare Monitors
    monitor = SystemResourceMonitor(interval_sec=0.05)
    tracemalloc.start()

    # 2. Execute & Time
    monitor.start()
    t_start = time.perf_counter()

    report = check_quality(filepath)

    t_end = time.perf_counter()
    monitor.stop()

    # 3. Collect Python Internal Memory & Stop Tracker
    _, peak_py_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # 4. Compute Metrics
    elapsed_time = t_end - t_start
    total_rows = report.get("rows", 0)
    total_cols = report.get("columns", 0)

    # OS RAM conversions (Bytes to MB)
    start_rss_mb = monitor.start_rss_bytes / (1024 * 1024)
    peak_rss_mb = monitor.peak_rss_bytes / (1024 * 1024)
    net_os_ram_mb = peak_rss_mb - start_rss_mb

    # Python Heap conversions
    peak_py_mb = peak_py_mem / (1024 * 1024)

    # CPU metrics
    avg_cpu = sum(monitor.cpu_samples) / len(monitor.cpu_samples) if monitor.cpu_samples else 0.0
    peak_cpu = max(monitor.cpu_samples) if monitor.cpu_samples else 0.0

    # Throughput
    rows_per_sec = (total_rows / elapsed_time) if elapsed_time > 0 else 0
    mb_per_sec = (file_size_mb / elapsed_time) if elapsed_time > 0 else 0

    # 5. Output Report
    print("\n" + "-" * 25 + " RESULTS " + "-" * 26)
    print(f"Processed Rows:        {total_rows:,}")
    print(f"Processed Columns:     {total_cols:,}")
    print(f"Execution Time:        {elapsed_time:.3f} seconds")
    print(f"Throughput:            {rows_per_sec:,.0f} rows/sec ({mb_per_sec:.2f} MB/sec)")
    print("-" * 60)
    print("CPU UTILIZATION:")
    print(f"  Average CPU:         {avg_cpu:.1f}%")
    print(f"  Peak CPU:            {peak_cpu:.1f}%")
    print("-" * 60)
    print("RAM METRICS:")
    print(f"  Python Heap Peak:    {peak_py_mb:.2f} MB  (Internal Python objects)")
    print(f"  OS Baseline RAM:     {start_rss_mb:.2f} MB")
    print(f"  OS Peak Process RAM: {peak_rss_mb:.2f} MB  (Actual system memory hit)")
    print(f"  Net OS RAM Used:     {net_os_ram_mb:.2f} MB  (Delta above baseline)")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    # Replace with a path to one of your real test datasets (guide on how to execute):
    # python -m tests.quality_benchmark (file location of your dataset e.g. assets/test_files/quality_test.csv)
    target_file = sys.argv[1] if len(sys.argv) > 1 else sys.exit(1)
    run_benchmark(target_file)
