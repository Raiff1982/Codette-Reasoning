import os
import time
import psutil

class HardwareMatrixTracker:
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        print("[ForgeEngine] Memory substrate tracking initialized.")
        print("[Systems] Target hardware locked: Intel Arc 140V (8GB Base)")

    def collect_memory_telemetry(self):
        """
        Captures the exact memory footprints of the active processing thread.
        """
        mem_info = self.process.memory_info()
        # Convert bytes to megabytes for clean, scannable reading
        rss_mb = mem_info.rss / (1024 * 1024)
        vms_mb = mem_info.vms / (1024 * 1024)
        
        print("\n--- 🌌 Cognitive Hardware Telemetry ---")
        print(f"[*] Living Memory Kernel RAM Footprint: {rss_mb:.2f} MB")
        print(f"[*] Virtual Memory Allocation Space:  {vms_mb:.2f} MB")
        
        # Check system-wide shared memory constraints
        virtual_mem = psutil.virtual_memory()
        print(f"[*] Total System Memory Capacity:     {virtual_mem.total / (1024**3):.2f} GB")
        print(f"[*] Active Memory Utilization:        {virtual_mem.percent}%")
        print("---------------------------------------")

    def execution_profile_loop(self, intervals: int = 3, delay: int = 2):
        """
        Runs a sequential trace across processing cycles to monitor spikes.
        """
        for cycle in range(intervals):
            print(f"\n[Cycle {cycle + 1}] Profiling framework state vectors...")
            self.collect_memory_telemetry()
            time.sleep(delay)

if __name__ == "__main__":
    # Instantiate the tracker within our architectural pipeline
    tracker = HardwareMatrixTracker()
    # Simulate a brief reasoning cycle monitoring window
    tracker.execution_profile_loop(intervals=2, delay=1)