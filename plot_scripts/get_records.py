from pathlib import Path
from get_last_modified_files_with_length_new import extract_datetime,find_det_csv_in_folder, csv_duration_seconds, get_fps
import os

def get_latest_entry(main_folder: Path):
    """
    Returns the path line (same format as print_report) for the latest
    CSV (in main folder) or det.csv (in subfolders).
    """

    rows = []

    # 1) Subfolders
    for entry in main_folder.iterdir():
        if not entry.is_dir():
            continue
        sort_key = extract_datetime(entry.name)
        det_csv = find_det_csv_in_folder(entry)
        if not det_csv:
            continue
        dur_s, nrows = csv_duration_seconds(det_csv)
        if dur_s <= 0:
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

    # 2) Top-level CSVs
    fps_main = get_fps(main_folder)
    for entry in main_folder.iterdir():
        if entry.is_file() and entry.suffix.lower() == '.csv':
            sort_key = extract_datetime(entry.name)
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

    if not rows:
        return None

    # Pick the latest (max datetime key)
    latest = max(rows, key=lambda r: r[0])
    _, origin, rel_path, dur_str, fps_str, nrows = latest
    path2dets = Path(rel_path).parent  # relative to main folder
    return Path(os.path.join(main_folder,path2dets))


if __name__ == "__main__":
    import sys
    main = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"../records_human_detection")
    print(get_latest_entry(main))
