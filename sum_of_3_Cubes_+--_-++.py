# pyMXYmulti_combined_checkpoint_fixed.py

import multiprocessing as mp
from multiprocessing import Manager
from queue import Empty as QueueEmpty
import threading
import time
import os
import json

# ============================
# ====== CONFIG (edit) =======
# ============================
M_START = 3_500_001
M_END   = 4_000_000

CORES             = 8
BLOCK_SIZE        = 50
PROGRESS_INTERVAL = 50

OUTPUT_PATH       = "pyMXYmulti_combined_output.txt"
CHECKPOINT_FILE   = "checkpoint.json"
CHECKPOINT_EVERY  = 50   # blocks
# ============================


# ── Checkpoint ────────────────────────────────────────────────────────────────
def save_checkpoint(next_m):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"next_m": next_m, "m_end": M_END}, f)


def load_checkpoint():
    if not os.path.exists(CHECKPOINT_FILE):
        return None

    try:
        with open(CHECKPOINT_FILE) as f:
            data = json.load(f)

        if data.get("m_end") != M_END:
            print("Checkpoint mismatch — starting fresh.")
            return None

        print(f"Resuming from m={data['next_m']:,}")
        return data["next_m"]

    except:
        return None


# ── Math ──────────────────────────────────────────────────────────────────────
def calculate_n(m, x, y):
    return (5*m + x)**3 - (4*m + y)**3 - (4*m + x)**3


def to_XYZ_plus(m, x, y):
    return (5*m+x), -(4*m+y), -(4*m+x)


def to_XYZ_minus(m, x, y):
    return -(5*m+x), (4*m+y), (4*m+x)


# ── Core logic ────────────────────────────────────────────────────────────────
def process_one_m(m):
    x = 0
    y = 0

    for _ in range(m):
        n = calculate_n(m, x, y)

        if n > 0:
            while n > 0:
                x += 1; y += 1
                n = calculate_n(m, x, y)

        if n < 0:
            while n < 0:
                x -= 1; y -= 1
                n = calculate_n(m, x, y)

        if 0 < n < 1000:
            X, Y, Z = to_XYZ_plus(m, x, y)
            yield f"{X}\t{Y}\t{Z}\t{n}"

        x += 1; y += 1
        n_neg = calculate_n(m, x, y)

        if n_neg < 0:
            n_minus = -n_neg
            if 0 < n_minus < 1000:
                X, Y, Z = to_XYZ_minus(m, x, y)
                yield f"{X}\t{Y}\t{Z}\t{n_minus}"

        y += 1


# ── Worker (UNCHANGED LOGIC) ──────────────────────────────────────────────────
def worker(proc_idx, task_q, out_q, completed_q, progress_interval):
    hits        = 0
    processed_m = 0
    t0          = time.time()

    while True:
        try:
            ms, me = task_q.get_nowait()
        except QueueEmpty:
            break

        for m in range(ms, me + 1):
            processed_m += 1

            if progress_interval and processed_m % progress_interval == 0:
                dt = time.time() - t0
                print(f"[P{proc_idx}] m={m} (+{progress_interval}), "
                      f"hits={hits}, time={dt:.1f}s", flush=True)

            for line in process_one_m(m):
                out_q.put(line)
                hits += 1

        # checkpoint tracking ONLY
        completed_q.put(me + 1)

    print(f"[P{proc_idx}] done. hits={hits}", flush=True)


# ── Writer (UNCHANGED — THIS IS IMPORTANT) ─────────────────────────────────────
SENTINEL = None

def writer_thread_fn(out_q, output_path, append):
    if not append:
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
            f.flush()   # 🔥 KEEP THIS

    finally:
        f.close()


# ── Block builder ─────────────────────────────────────────────────────────────
def build_blocks(m_start, m_end, block_size):
    a = m_start
    while a <= m_end:
        b = min(a + block_size - 1, m_end)
        yield (a, b)
        a = b + 1


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    resume_m = load_checkpoint()
    start_m  = resume_m if resume_m else M_START
    append   = resume_m is not None

    num_procs  = max(1, CORES)
    total_m    = M_END - start_m + 1
    num_blocks = (total_m + BLOCK_SIZE - 1) // BLOCK_SIZE

    print(f"Scanning m in [{start_m:,}, {M_END:,}] ({total_m:,})")
    print(f"Cores: {num_procs} | Blocks: {num_blocks:,}")
    print(f"Checkpoint every {CHECKPOINT_EVERY} blocks")

    blocks_done = 0
    last_m      = start_m

    with Manager() as mgr:
        task_q      = mgr.Queue()
        completed_q = mgr.Queue()

        for blk in build_blocks(start_m, M_END, BLOCK_SIZE):
            task_q.put(blk)

        out_q = mp.Queue(maxsize=total_m)

        wt = threading.Thread(
            target=writer_thread_fn,
            args=(out_q, OUTPUT_PATH, append),
            daemon=True
        )
        wt.start()

        procs = []
        for i in range(1, num_procs + 1):
            p = mp.Process(
                target=worker,
                args=(i, task_q, out_q, completed_q, PROGRESS_INTERVAL)
            )
            p.start()
            procs.append(p)

        alive = num_procs
        while alive > 0:

            while True:
                try:
                    next_m = completed_q.get_nowait()
                    blocks_done += 1
                    last_m = max(last_m, next_m)

                    if blocks_done % CHECKPOINT_EVERY == 0:
                        save_checkpoint(last_m)
                        print(f"Checkpoint at m={last_m:,}", flush=True)

                except QueueEmpty:
                    break

            alive = sum(1 for p in procs if p.is_alive())
            time.sleep(0.5)

        for p in procs:
            p.join()

        save_checkpoint(M_END + 1)
        print("Final checkpoint saved")

        out_q.put(SENTINEL)
        wt.join()

    print("All done.")
    input("\nPress ENTER to close...")


if __name__ == "__main__":
    mp.freeze_support()
    main()
