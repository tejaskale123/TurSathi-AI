from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
import hashlib
import csv
import math

SOURCE = Path("PPLD_extracted/PPLD")
OUT = Path("reports/duplicate_review")
OUT.mkdir(parents=True, exist_ok=True)

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
                    "path": str(file.resolve())
                })
            except Exception as e:
                print("READ ERROR:", file, e)

groups = {}

for row in rows:
    groups.setdefault(row["hash"], []).append(row)

conflicts = []

for h, group in groups.items():
    classes = sorted(set(x["class"] for x in group))
    if len(classes) > 1:
        conflicts.append((h, group))

conflicts.sort(key=lambda x: x[0])

csv_path = OUT / "cross_class_duplicates.csv"

with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Group","SHA256","Classes","File"])

    for i, (h, group) in enumerate(conflicts, 1):
        classes = " | ".join(sorted(set(x["class"] for x in group)))
        for item in group:
            writer.writerow([i, h, classes, item["path"]])

print("Cross-class duplicate groups:", len(conflicts))
print("CSV:", csv_path)

# Create visual sheets
PER_SHEET = 15
COLS = 3
TILE_W = 360
TILE_H = 330

for sheet_start in range(0, len(conflicts), PER_SHEET):

    batch = conflicts[sheet_start:sheet_start + PER_SHEET]
    sheet_no = sheet_start // PER_SHEET + 1
    rows_count = math.ceil(len(batch) / COLS)

    sheet = Image.new("RGB", (COLS * TILE_W, rows_count * TILE_H), "white")
    draw = ImageDraw.Draw(sheet)

    for local_index, (h, group) in enumerate(batch):

        x = (local_index % COLS) * TILE_W
        y = (local_index // COLS) * TILE_H

        # Same image content appears in multiple classes.
        # Load only the first copy for visual inspection.
        image_path = Path(group[0]["path"])

        try:
            img = Image.open(image_path).convert("RGB")
            img.thumbnail((330, 245))

            px = x + (TILE_W - img.width) // 2
            py = y + 10

            sheet.paste(img, (px, py))

            group_no = sheet_start + local_index + 1
            classes = " / ".join(sorted(set(item["class"] for item in group)))

            draw.text(
                (x + 10, y + 265),
                f"GROUP {group_no}",
                fill="black"
            )

            draw.text(
                (x + 10, y + 285),
                classes,
                fill="black"
            )

            draw.text(
                (x + 10, y + 305),
                f"Copies: {len(group)}",
                fill="black"
            )

        except Exception as e:
            draw.text(
                (x + 10, y + 20),
                f"IMAGE ERROR: {image_path.name}",
                fill="red"
            )
            print("IMAGE ERROR:", image_path, e)

    output = OUT / f"duplicate_sheet_{sheet_no:02d}.jpg"
    sheet.save(output, quality=95)
    print("Created:", output)

print("\nVISUAL REVIEW COMPLETE")
print("NO FILES WERE DELETED.")
