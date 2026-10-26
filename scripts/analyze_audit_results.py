import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open("scripts/datasets_audit_summary.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print("=" * 80)
print("1. SUMMARY OF DATASET FOLDERS & IMAGE COUNTS")
print("=" * 80)

for name, info in sorted(data["folder_summary"].items()):
    print(f"Directory: datasets/{name}/")
    print(f"  Total Files: {info['total_files']} | Images: {info['image_files']} | Non-images: {info['non_image_files']}")
    print(f"  Disk Size: {info['total_mb']} MB | Unique SHA-256 Hashes: {info['unique_hashes']}")
    print("  Structure / Splits & Classes:")
    for sp, cls_counts in sorted(info["splits"].items()):
        total_in_split = sum(cls_counts.values())
        print(f"    [{sp}] ({total_in_split} images):")
        for cls, count in sorted(cls_counts.items()):
            print(f"      - {cls}: {count}")
    print()

print("=" * 80)
print("2. STANDALONE FILES IN datasets/")
print("=" * 80)
for sf in data.get("standalone_files", []):
    print(f"File: {sf['path']} | Size: {sf['size_bytes']:,} bytes | SHA-256: {sf['sha256'][:16]}...")
print()

print("=" * 80)
print("3. INTER-FOLDER HASH OVERLAP MATRIX (Exact SHA-256 Duplication)")
print("=" * 80)
overlap = data["overlap_matrix"]
folders = sorted(overlap.keys())

for f1 in folders:
    shared_partners = []
    h1_count = data["folder_summary"][f1]["unique_hashes"]
    for f2 in folders:
        if f1 == f2:
            continue
        stats = overlap[f1][f2]
        shared = stats["shared_hashes"]
        if shared > 0:
            pct1 = stats["pct_of_f1"]
            pct2 = stats["pct_of_f2"]
            shared_partners.append((f2, shared, pct1, pct2))

    if shared_partners:
        print(f"datasets/{f1}/ ({h1_count} unique hashes) overlaps with:")
        for f2, shared, pct1, pct2 in sorted(shared_partners, key=lambda x: x[1], reverse=True):
            print(f"  -> datasets/{f2}/: {shared} shared hashes ({pct1}% of {f1}, {pct2}% of {f2})")
    else:
        print(f"datasets/{f1}/ ({h1_count} unique hashes): NO overlaps with any other folder (100% unique)")
    print()

print("=" * 80)
print("4. LABEL CONFLICTS ACROSS DATASETS")
print("=" * 80)
conflicts = data.get("total_label_conflicts", 0)
print(f"Total images with conflicting class labels across datasets: {conflicts}")
for idx, c in enumerate(data.get("label_conflicts_sample", [])[:10], 1):
    print(f"Conflict #{idx}: SHA256={c['sha256'][:16]}... Classes={c['classes']}")
    for occ in c["occurrences"]:
        print(f"   [{occ['folder']}] {occ['split']}/{occ['class']} -> {occ['path']}")
    print()

print("=" * 80)
print("5. TOTAL DUPLICATE HASHES IN REPO")
print("=" * 80)
print(f"Total unique hashes appearing more than once: {data.get('total_duplicate_hashes')}")
top_dups = data.get("top_duplicates_sample", [])
print(f"Top 10 highest-frequency duplicate images:")
for idx, d in enumerate(top_dups[:10], 1):
    print(f"Duplicate #{idx} (Copies: {d['count']}, SHA: {d['sha256'][:16]}...):")
    for p in d["paths"]:
        print(f"   - {p}")
    print()
