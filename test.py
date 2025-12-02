#!/usr/bin/env python3
"""
Graceful IP-range scanner.
- Safer defaults
- Catches KeyboardInterrupt and saves partial results
- Modes: edge_only, sample, full
"""

import ipaddress
import platform
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import csv
import time
import sys

# ---------- EDIT THESE ----------
INPUT_FILE = Path(r"C:\Users\ASUS\Downloads\angry_ip_ranges_tsv.txt")
OUTPUT_TXT = Path("live_ips_partial.txt")
OUTPUT_CSV = Path("live_ips_partial.csv")

mode = "sample"        # "edge_only", "sample", or "full"
sample_step = 256
max_workers = 50       # try 20-100 depending on your CPU
ping_timeout_sec = 0.7 # seconds (Windows uses ms flag; non-windows use seconds)
# --------------------------------

IS_WINDOWS = platform.system().lower().startswith("win")

def make_ping_cmd(ip):
    if IS_WINDOWS:
        # -n 1  -> 1 echo, -w timeout in ms
        return ["ping", "-n", "1", "-w", str(int(ping_timeout_sec * 1000)), str(ip)]
    else:
        # -c 1 -> 1 echo, -W timeout in seconds (integer)
        # use int(max(1, round(ping_timeout_sec))) so ping accepts it
        return ["ping", "-c", "1", "-W", str(max(1, int(round(ping_timeout_sec)))), str(ip)]

def parse_ranges_from_file(path):
    ranges = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.replace("\t", " ").split()
            if len(parts) >= 2:
                start, end = parts[0], parts[1]
                try:
                    s = ipaddress.IPv4Address(start)
                    e = ipaddress.IPv4Address(end)
                    if int(e) < int(s):
                        s, e = e, s
                    ranges.append((str(s), str(e)))
                except Exception:
                    continue
    return ranges

def ips_to_test_for_range(start_s, end_s, mode="sample", step=256):
    start = int(ipaddress.IPv4Address(start_s))
    end = int(ipaddress.IPv4Address(end_s))
    size = end - start + 1
    if mode == "edge_only":
        yield str(ipaddress.IPv4Address(start))
        if size > 1:
            yield str(ipaddress.IPv4Address(end))
        return
    if mode == "full":
        for i in range(start, end + 1):
            yield str(ipaddress.IPv4Address(i))
        return
    # sample mode
    yield str(ipaddress.IPv4Address(start))
    if size > 1:
        yield str(ipaddress.IPv4Address(end))
    if size <= step:
        for i in range(start, end + 1):
            yield str(ipaddress.IPv4Address(i))
    else:
        cur = start + step
        while cur < end:
            yield str(ipaddress.IPv4Address(cur))
            cur += step

def ping_ip(ip):
    cmd = make_ping_cmd(ip)
    try:
        # Use subprocess.run with timeout a bit larger than ping timeout to protect hung pings
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=max(2, ping_timeout_sec + 1))
        return (ip, p.returncode == 0)
    except subprocess.TimeoutExpired:
        return (ip, False)
    except Exception:
        return (ip, False)

def save_results(live_entries, txt_path, csv_path):
    # Append mode so partial results are kept
    with open(txt_path, "w", encoding="utf-8") as ftxt:
        for ip, rng in live_entries:
            ftxt.write(f"{ip}\t{rng}\n")
    with open(csv_path, "w", newline="", encoding="utf-8") as fcsv:
        writer = csv.writer(fcsv)
        writer.writerow(["ip", "source_range"])
        for ip, rng in live_entries:
            writer.writerow([ip, rng])

def main():
    if not INPUT_FILE.exists():
        print(f"Input file not found: {INPUT_FILE}")
        sys.exit(1)

    ranges = parse_ranges_from_file(INPUT_FILE)
    if not ranges:
        print("No valid ranges found.")
        sys.exit(1)

    # build candidate list
    to_test = []
    for start, end in ranges:
        for ip in ips_to_test_for_range(start, end, mode=mode, step=sample_step):
            to_test.append((ip, f"{start}-{end}"))

    total = len(to_test)
    print(f"Mode={mode}. Candidate IPs to test: {total}. Workers={max_workers}. Timeout={ping_timeout_sec}s")
    if total == 0:
        print("Nothing to test.")
        return

    live_entries = []
    started = time.time()
    processed = 0

    executor = ThreadPoolExecutor(max_workers=max_workers)
    futures = {executor.submit(ping_ip, ip): (ip, rng) for ip, rng in to_test}

    try:
        for fut in as_completed(futures):
            ip, rng = futures[fut]
            try:
                ip_res, alive = fut.result()
            except Exception:
                alive = False
            processed += 1
            # quick progress print every 50 processed
            if processed % 50 == 0 or alive:
                elapsed = time.time() - started
                rate = processed / elapsed if elapsed > 0 else 0
                print(f"[{processed}/{total}] {ip} -> {'LIVE' if alive else 'dead'}  (rate {rate:.1f} ip/s)")
            if alive:
                live_entries.append((ip, rng))
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received — shutting down executor and saving partial results...")
        # try to cancel running futures (best-effort)
        executor.shutdown(wait=False, cancel_futures=True)
        save_results(live_entries, OUTPUT_TXT, OUTPUT_CSV)
        print(f"Saved partial {len(live_entries)} live entries to {OUTPUT_TXT} and {OUTPUT_CSV}")
        return
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # normal shutdown
        executor.shutdown(wait=False)

    # finished normally
    save_results(live_entries, OUTPUT_TXT, OUTPUT_CSV)
    print(f"\nFinished. Live hosts found: {len(live_entries)}")
    print(f"Results saved to {OUTPUT_TXT} and {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
