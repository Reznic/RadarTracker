import os
import re
import time
import pandas as pd
from datetime import datetime
from pathlib import Path

def get_fps(folder_path: Path):
    """
    Look for any .cfg in the given folder and try to parse frameCfg line.
    Returns FPS (float) or None if not found / unparsable.
    """
    frame_period = None
    cfg_path = None
    for p in folder_path.iterdir():
        if p.suffix.lower() == ".cfg" and p.is_file():
            cfg_path = p
            break
    if not cfg_path:
        return None

    try:
        with cfg_path.open('r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('%'):
                    continue
                if s.startswith('frameCfg'):
                    parts = s.split()
                    # defensively ensure index exists
                    if len(parts) >= 6:
                        frame_period = float(parts[5])  # ms
                        break
        if frame_period and frame_period > 0:
            return 1.0 / (frame_period / 1000.0)
    except Exception:
        return None
    return None

def extract_datetime(name: str):
    """
    Extract epoch from any token like YYYYMMDD_HHMMSS inside 'name'.
    Returns epoch timestamp (float) or 0 if not found/unparsable.
    """
    m = re.search(r"(\d{8}_\d{6})", name)
    if not m:
        return 0
    try:
        return datetime.strptime(m.group(1), "%Y%m%d_%H%M%S").timestamp()
    except Exception:
        return 0

def csv_duration_seconds(csv_path: Path):
    """
    Reads CSV and computes duration from 'timestamp' column (max - min).
    Returns (duration_seconds:int or 0) and row_count (int) for convenience.
    """
    try:
        df = pd.read_csv(csv_path, header=0)
    except Exception:
        return 0, 0
    if 'timestamp' not in df.columns:
        return 0, len(df)
    ts = pd.to_numeric(df['timestamp'], errors='coerce').dropna()
    if ts.empty:
        return 0, len(df)
    dur = int(ts.max() - ts.min())
    if dur < 0:
        dur = 0
    return dur, len(df)

def find_det_csv_in_folder(folder: Path):
    """
    Prefer an exact 'det.csv' (case-insensitive). If not found, try '*det*.csv'.
    If still not found, return None.
    """
    # exact det.csv (case-insensitive)
    for p in folder.iterdir():
        if p.is_file() and p.suffix.lower() == '.csv' and p.name.lower() == 'det.csv':
            return p
    # any csv that contains 'det'
    cands = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == '.csv' and 'det' in p.name.lower()]
    if cands:
        # pick the first to keep it deterministic-ish
        return sorted(cands)[0]
    return None

def print_report(main_folder: Path,days_ago=1):
    """
    Only inspects:
      1) Immediate subfolders of 'main_folder' (each should contain a det.csv)
      2) CSV files directly in 'main_folder'
    Sorts all results by extracted datetime (folder name for subfolders, file name for top-level CSVs).
    """
    now = time.time()
    days_ago_time = now - 86400 * days_ago  # 2 days ago

    rows = []

    # 1) Subfolders
    for entry in main_folder.iterdir():
        if not entry.is_dir():
            continue
        sort_key = extract_datetime(entry.name)
        if sort_key < days_ago_time:
            continue
        det_csv = find_det_csv_in_folder(entry)
        if not det_csv:
            continue

        dur_s, nrows = csv_duration_seconds(det_csv)
        if dur_s <= 0:
            # keep or skip; here we skip zero-length
            continue

        minutes, seconds = divmod(dur_s, 60)
        dur_str = f"{minutes:02d}:{seconds:02d}"

        fps = get_fps(entry)
        fps_str = f"{fps:.2f}" if fps else "None"

        rows.append((
            sort_key,
            f"[FOLDER] {entry.name}",
            str(det_csv.relative_to(main_folder)),
            dur_str,
            fps_str,
            nrows
        ))

    # 2) CSVs directly in main folder
    fps_main = get_fps(main_folder)  # FPS for top-level CSVs (if any .cfg in main)
    for entry in main_folder.iterdir():
        if entry.is_file() and entry.suffix.lower() == '.csv':
            sort_key = extract_datetime(entry.name)
            if sort_key < days_ago_time:
                continue
            dur_s, nrows = csv_duration_seconds(entry)
            if dur_s <= 0:
                continue
            minutes, seconds = divmod(dur_s, 60)
            dur_str = f"{minutes:02d}:{seconds:02d}"
            fps_str = f"{fps_main:.2f}" if fps_main else "None"

            rows.append((
                sort_key,
                "[MAIN] CSV",
                entry.name,
                dur_str,
                fps_str,
                nrows
            ))

    # sort by datetime key
    rows.sort(key=lambda r: r[0])

    # print
    print(f"Scan root: {main_folder.resolve()}")
    print("Format: when available, FPS is from a .cfg in the same folder.\n")
    for _, origin, rel_path, dur_str, fps_str, nrows in rows:
        # keep your original-style line but clarified
        path2dets = Path(rel_path).parent  # relative to main folder
        print(
            f"path2dets = Path(r\"../records_human_detection/{path2dets}\")  # "
            f"Duration: {dur_str} | FPS: {fps_str} | dets: {nrows}"
        )

if __name__ == "__main__":
    # If you want to pass it as an argument:
    import sys

    days_ago = 5
    # folder = "records_radom_calib"
    folder = "records_human_detection"
    # folder = "records"

    main = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(f"{folder}")
    print_report(main,days_ago=days_ago)
