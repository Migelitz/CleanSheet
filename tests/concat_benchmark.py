import os
import threading
import time
import tracemalloc
from pathlib import Path

import psutil
import pygame
import requests
from dotenv import load_dotenv

from src.cleansheet.concatenator.tab_concat import concat_files
from src.cleansheet.quality.quality_checker import check_quality

# load all env
load_dotenv()


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


def run_benchmark(files: list[str], chunksize: int, output_extension: str) -> None:

    input_size_mb = []

    for file in files:
        if not Path(file).absolute().exists():
            print(f"Error: File not found -> {file}")
            return

        input_size_mb.append(Path(file).stat().st_size / (1024 * 1024))

    print("=" * 60)

    for i in range(len(files)):
        print(f"INPUT: {Path(files[i]).name}")
        print(f"File Size:    {input_size_mb[i]:.2f} MB")
        print()

    print(f"Total Input: {sum(input_size_mb):.2f} MB")

    print("=" * 60)

    output_path = Path("tests").absolute() / f"benchmark_merged.{output_extension}"

    # 1. Prepare Monitors
    monitor = SystemResourceMonitor(interval_sec=0.05)
    tracemalloc.start()

    # 2. Execute & Time
    monitor.start()
    t_start = time.perf_counter()

    concat_files(
        files=files, output_folder=str(output_path.parent), output_filename=output_path.name, chunksize=chunksize
    )

    t_end = time.perf_counter()
    monitor.stop()

    # 3. Collect Python Internal Memory & Stop Tracker
    _, peak_py_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    # 4. Verify output
    if not output_path.exists():
        print("ERROR: Concatenator did not create the output file.")
        return

    output_size_mb = output_path.stat().st_size / (1024 * 1024)

    # 5. Inspect output for row/column information
    #    This is outside the timed section.
    report = check_quality(Path(output_path).absolute())
    total_rows = report.get("rows", 0)
    total_cols = report.get("columns", 0)

    # 6. Compute Metrics
    elapsed_time = t_end - t_start

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
    mb_per_sec = (sum(input_size_mb) / elapsed_time) if elapsed_time > 0 else 0

    # 7. Output Report
    print("\n" + "-" * 25 + " RESULTS " + "-" * 26)
    print(f"Input Files :          {len(files):,}")
    print(f"Input Size  :          {sum(input_size_mb):.2f} MB")
    print(f"Output Size :          {output_size_mb:.2f} MB")
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
    print()


if __name__ == "__main__":
    import sys

    # Replace with a path to one of your real test datasets (guide on how to execute):
    # python -m tests.concat_benchmark (file location of the dataset e.g. assets/test_files/quality_test.xlsx) (file location again)... (extension name) (number of run here) (chunksize)
    # add as many files you want to concatenate
    # -3 to take account of the run and chunksize in len(sys.argv)
    target_file = sys.argv[1 : len(sys.argv) - 3] if len(sys.argv) - 3 > 1 else sys.exit(1)
    output_ext = sys.argv[-3] if len(sys.argv) - 3 > 1 else sys.exit(1)
    run = int(sys.argv[-2]) if len(sys.argv) - 3 > 1 else sys.exit(1)
    chunksize = int(sys.argv[-1]) if len(sys.argv) - 3 > 1 else sys.exit(1)

    for _ in range(run):
        run_benchmark(target_file, chunksize, output_ext)

    # IF active in laptop
    # pygame.mixer.init()

    # pygame.mixer.music.load("assets/music/alarm.mp3")

    # pygame.mixer.music.play(-1)

    # pygame.mixer.music.set_volume(1.0)

    # print("Press Ctrl+C to stop...")

    # try:
    #     while pygame.mixer.music.get_busy():
    #         time.sleep(1)
    # except KeyboardInterrupt:
    #     pygame.mixer.music.stop()

    # IF inactive in laptop
    NTFY_TOPIC = os.getenv("NTFY_TOPIC")

    def send_alarm(title: str, message: str):
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": "urgent",
                "Tags": "rotating_light,alarm_clock",
            },
            timeout=10,
        )

    send_alarm(title="Benchmark Complete!", message="You may look at the results now.")
