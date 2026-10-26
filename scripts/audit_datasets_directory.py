import os
import sys
import hashlib
import json
from pathlib import Path
from collections import defaultdict

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = REPO_ROOT / "datasets"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

def get_sha256(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def audit():
    print(f"Starting audit of: {DATASETS_DIR}")
    if not DATASETS_DIR.exists():
        print("ERROR: datasets/ directory does not exist.")
        return

    # 1. Traverse all files
    all_files = []
    hash_to_files = defaultdict(list)
    folder_summary = defaultdict(lambda: {
        "total_files": 0,
        "image_files": 0,
        "non_image_files": 0,
        "total_bytes": 0,
        "splits": defaultdict(lambda: defaultdict(int)),
        "classes": defaultdict(int),
        "hashes": set(),
        "subdirs": set(),
        "files_list": [],
    })

    top_level_items = sorted(os.listdir(DATASETS_DIR))
    print(f"Top-level items in datasets/: {len(top_level_items)}")

    standalone_files = []

    for item in top_level_items:
        item_path = DATASETS_DIR / item
        if item_path.is_file():
            size = item_path.stat().st_size
            sha = get_sha256(item_path)
            standalone_files.append({
                "name": item,
                "path": str(item_path.relative_to(REPO_ROOT)),
                "size_bytes": size,
                "sha256": sha,
            })
            hash_to_files[sha].append(str(item_path.relative_to(REPO_ROOT)))
            continue

        # item is a directory
        top_name = item
        for root, dirs, files in os.walk(item_path):
            rel_root = Path(root).relative_to(item_path)
            parts = rel_root.parts

            if parts:
                folder_summary[top_name]["subdirs"].add("/".join(parts))

            for f in files:
                f_path = Path(root) / f
                rel_repo_path = str(f_path.relative_to(REPO_ROOT)).replace("\\", "/")
                size = f_path.stat().st_size
                ext = f_path.suffix.lower()
                is_img = ext in IMAGE_EXTENSIONS

                sha = get_sha256(f_path)
                hash_to_files[sha].append(rel_repo_path)

                info = folder_summary[top_name]
                info["total_files"] += 1
                info["total_bytes"] += size
                info["hashes"].add(sha)
                info["files_list"].append({
                    "path": rel_repo_path,
                    "sha256": sha,
                    "size": size,
                    "is_img": is_img,
                    "ext": ext
                })

                if is_img:
                    info["image_files"] += 1
                    # Attempt to parse split and class
                    # Check common patterns:
                    # pattern A: <top>/<split>/<class>/<filename>
                    # pattern B: <top>/<class>/<filename>
                    if len(parts) >= 2 and parts[0] in ("train", "val", "test", "quarantine", "real_world_test"):
                        split = parts[0]
                        cls = parts[1]
                        info["splits"][split][cls] += 1
                        info["classes"][cls] += 1
                    elif len(parts) == 1 and parts[0] in ("train", "val", "test"):
                        split = parts[0]
                        info["splits"][split]["_unspecified_"] += 1
                    elif len(parts) >= 1:
                        cls = parts[0]
                        info["splits"]["_no_split_"][cls] += 1
                        info["classes"][cls] += 1
                    else:
                        info["splits"]["_flat_"]["_root_"] += 1
                else:
                    info["non_image_files"] += 1

    # 2. Inter-folder overlap / subset analysis
    top_folders = sorted([k for k in folder_summary.keys()])
    overlap_matrix = {}
    for i, f1 in enumerate(top_folders):
        overlap_matrix[f1] = {}
        h1 = folder_summary[f1]["hashes"]
        for j, f2 in enumerate(top_folders):
            h2 = folder_summary[f2]["hashes"]
            shared = len(h1.intersection(h2))
            overlap_matrix[f1][f2] = {
                "shared_hashes": shared,
                "pct_of_f1": round(shared / len(h1) * 100, 2) if len(h1) > 0 else 0,
                "pct_of_f2": round(shared / len(h2) * 100, 2) if len(h2) > 0 else 0,
            }

    # 3. Label conflicts across folders
    # Map hash -> set of (folder, split, class, filename)
    hash_labels = defaultdict(list)
    for top_name, data in folder_summary.items():
        for f in data["files_list"]:
            if f["is_img"]:
                # determine label
                p_parts = Path(f["path"]).parts
                # p_parts: ('datasets', top_name, ...)
                sub = p_parts[2:]
                cls = "UNKNOWN"
                split = "NONE"
                if len(sub) >= 2 and sub[0] in ("train", "val", "test", "quarantine", "real_world_test"):
                    split = sub[0]
                    cls = sub[1]
                elif len(sub) == 1:
                    cls = sub[0]
                hash_labels[f["sha256"]].append({
                    "folder": top_name,
                    "split": split,
                    "class": cls,
                    "path": f["path"],
                    "filename": Path(f["path"]).name
                })

    label_conflicts = []
    for sha, occurrences in hash_labels.items():
        if len(occurrences) > 1:
            classes = set(o["class"] for o in occurrences if o["class"] != "UNKNOWN")
            if len(classes) > 1:
                label_conflicts.append({
                    "sha256": sha,
                    "classes": list(classes),
                    "occurrences": occurrences
                })

    # 4. Duplicate groups (hashes with count > 1)
    dup_groups = []
    for sha, paths in hash_to_files.items():
        if len(paths) > 1:
            dup_groups.append({
                "sha256": sha,
                "count": len(paths),
                "paths": paths
            })

    # Save complete raw audit json
    audit_results = {
        "datasets_path": str(DATASETS_DIR),
        "total_top_folders": len(top_folders),
        "standalone_files": standalone_files,
        "folder_summary": {
            k: {
                "total_files": v["total_files"],
                "image_files": v["image_files"],
                "non_image_files": v["non_image_files"],
                "total_bytes": v["total_bytes"],
                "total_mb": round(v["total_bytes"] / (1024 * 1024), 2),
                "unique_hashes": len(v["hashes"]),
                "subdirs": sorted(list(v["subdirs"])),
                "splits": {s: dict(c) for s, c in v["splits"].items()},
                "classes": dict(v["classes"]),
            }
            for k, v in folder_summary.items()
        },
        "overlap_matrix": overlap_matrix,
        "total_duplicate_hashes": len(dup_groups),
        "total_label_conflicts": len(label_conflicts),
        "label_conflicts_sample": label_conflicts[:20],
        "top_duplicates_sample": sorted(dup_groups, key=lambda x: x["count"], reverse=True)[:30],
    }

    out_json = REPO_ROOT / "scripts" / "datasets_audit_summary.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)

    print(f"Audit completed successfully! Saved to: {out_json}")

if __name__ == "__main__":
    audit()
