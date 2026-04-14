# dynamic_blocks_sum_three_cubes_writer.py
# Dynamic block scheduling + threaded writer (no file locks in workers).
# Workers push result lines to a multiprocessing.Queue; a single writer
# thread in the main process drains/batches and writes to disk.

import multiprocessing as mp
from multiprocessing import Manager
from queue import Empty as QueueEmpty
import threading
import time
import os

# ============================
# ====== CONFIG (edit) =======
# ============================
M_START = 5_310_001
M_END   = 5_350_000

CORES = 5                   # runs exactly this many cores regardless of CPU count
PROGRESS_INTERVAL = 50      # per worker: print every this many m's processed
OUTPUT_PATH = "output.txt"
# ============================

# ---------- your math (unchanged) ----------
def calculate_n(m, x, y):
    return (5 * m + x) ** 3 - (4 * m + y) ** 3 - (4 * m + x) ** 3

def to_XYZ(m, x, y):
    X = (5 * m + x)
    Y = -(4 * m + y)
    Z = -(4 * m + x)
    return X, Y, Z

def process_one_m(m):
    """
    Run your original (x,y) walk for a single m and yield lines "X\tY\tZ\tn".
    The zero always occurs at ridge m+1, so we stop after m ridges
    instead of scanning until n==0 -- eliminates one full ridge per m.
    """
    x = 0
    y = 0
    for _ in range(m):
        n = calculate_n(m, x, y)

        if n > 0:
            while n > 0:
                x += 1
                y += 1
                n = calculate_n(m, x, y)

        if n < 0:
            while n < 0:
                x -= 1
                y -= 1
                n = calculate_n(m, x, y)

        if 0 < n < 1000:
            X, Y, Z = to_XYZ(m, x, y)
            yield f"{X}\t{Y}\t{Z}\t{n}"

        y += 1

# ---------- threaded writer ----------
SENTINEL = None

def writer_thread_fn(out_q, output_path):
    """
    Drain out_q and write to disk immediately on each hit.
    Stops when SENTINEL is received.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# X\tY\tZ\tn\n")

    f = open(output_path, "a", encoding="utf-8")
    try:
        while True:
            try:
                item = out_q.get(timeout=1.0)
            except Exception:
                continue

            if item is SENTINEL:
                # Drain any remaining items
                while True:
                    try:
                        nxt = out_q.get_nowait()
                        if nxt is not SENTINEL:
                            f.write(nxt + "\n")
                    except QueueEmpty:
                        break
                f.flush()
                break

            f.write(item + "\n")
            f.flush()
    finally:
        f.close()

# ---------- worker: dynamic blocks, push to queue ----------
def worker(proc_idx, task_q, out_q, progress_interval):
    hits = 0
    processed_m = 0
    t0 = time.time()
    _process_one_m = process_one_m

    while True:
        try:
            ms, me = task_q.get_nowait()
        except QueueEmpty:
            break

        for m in range(ms, me + 1):
            processed_m += 1
            if progress_interval and (processed_m % progress_interval == 0):
                dt = time.time() - t0
                print(f"[P{proc_idx}] m={m} (+{progress_interval}), hits={hits}, time={dt:.1f}s", flush=True)

            for line in _process_one_m(m):
                out_q.put(line)
                hits += 1

    print(f"[P{proc_idx}] done. hits={hits}", flush=True)

# ---------- block builder ----------
def build_blocks(m_start, m_end, num_cores):
    """One block per core so all cores stay fully busy."""
    total      = m_end - m_start + 1
    block_size = max(1, total // num_cores)
    a = m_start
    while a <= m_end:
        b = min(a + block_size - 1, m_end)
        yield (a, b)
        a = b + 1

def main():
    # Use exactly CORES workers -- no cap against cpu_count
    num_procs = max(1, CORES)
    total_m   = M_END - M_START + 1
    block_size = max(1, total_m // num_procs)

    print(f"Scanning m in [{M_START:,}, {M_END:,}]  ({total_m:,} values)")
    print(f"Using {num_procs} worker(s)  |  Block size: {block_size:,} (auto)")
    print(f"Output -> {os.path.abspath(OUTPUT_PATH)}")

    # Queue size: auto-scaled to total_m so it never blocks workers
    queue_maxsize = total_m

    with Manager() as mgr:
        task_q = mgr.Queue()
        for blk in build_blocks(M_START, M_END, num_procs):
            task_q.put(blk)

        out_q = mp.Queue(maxsize=queue_maxsize)

        # Start writer thread
        wt = threading.Thread(
            target=writer_thread_fn,
            args=(out_q, OUTPUT_PATH),
            daemon=True
        )
        wt.start()

        # Launch exactly num_procs workers
        procs = []
        for i in range(1, num_procs + 1):
            p = mp.Process(target=worker,
                           args=(i, task_q, out_q, PROGRESS_INTERVAL),
                           daemon=False)
            p.start()
            procs.append(p)

        for p in procs:
            p.join()

        out_q.put(SENTINEL)
        wt.join()

    print("All done.")
    input("\nPress ENTER to close...")

if __name__ == "__main__":
    try:
        mp.freeze_support()
        main()
    except Exception as e:
        import traceback
        print("\nERROR:", e)
        traceback.print_exc()
        input("\nPress ENTER to close...")