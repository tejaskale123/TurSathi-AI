from pathlib import Path
import hashlib
import shutil

SOURCE = Path("PPLD_extracted/PPLD")
BACKUP = Path("PPLD_extracted/PPLD_backup_before_duplicate_removal")

rows = []

for class_dir in SOURCE.iterdir():
    if not class_dir.is_dir():
        continue

    for file in class_dir.iterdir():
        if file.is_file() and file.suffix.lower() in [".jpg",".jpeg",".png",".webp"]:
            try:
                h = hashlib.sha256(file.read_bytes()).hexdigest()

                rows.append({
                    "hash": h,
                    "class": class_dir.name,
                    "path": file
                })

            except Exception as e:
                print("READ ERROR:", file, e)

groups = {}

for row in rows:
    groups.setdefault(row["hash"], []).append(row)

deleted = []
kept = []

for h, group in groups.items():

    if len(group) <= 1:
        continue

    classes = set(item["class"] for item in group)

    # Cross-class exact duplicate:
    # remove every copy because the correct label cannot be inferred safely.
    if len(classes) > 1:

        for item in group:
            if item["path"].exists():
                deleted.append(str(item["path"]))
                item["path"].unlink()

    # Same-class exact duplicate:
    # keep first, remove remaining copies.
    else:

        group = sorted(group, key=lambda x: str(x["path"]))

        kept.append(str(group[0]["path"]))

        for item in group[1:]:
            if item["path"].exists():
                deleted.append(str(item["path"]))
                item["path"].unlink()

print()
print("=" * 70)
print("DUPLICATE REMOVAL COMPLETE")
print("=" * 70)

print(f"Files deleted : {len(deleted)}")
print(f"Files kept as duplicate representative : {len(kept)}")

print()
print("Backup remains at:")
print(BACKUP)

print()
print("Deleted files:")
for path in deleted:
    print(path)

print()
print("Original source cleaned.")
print("Backup was NOT modified.")
print("Clean training dataset was NOT modified.")
