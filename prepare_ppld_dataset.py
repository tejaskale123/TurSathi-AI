from pathlib import Path
from collections import defaultdict
from PIL import Image, ImageOps, ImageEnhance
import hashlib
import random
import shutil

# ============================================================
# TUR SATHI AI - PPLD DATASET PREPARATION
# ============================================================
# Original dataset is NEVER modified.
#
# Input:
#   PPLD_extracted/PPLD
#
# Output:
#   PPLD_processed/
#       train/
#       val/
#       test/
#
# Rules:
# 1. Cross-class exact duplicates are excluded.
# 2. Same-class exact duplicates are reduced to one copy.
# 3. Train / validation / test split = 70 / 15 / 15.
# 4. Augmentation is applied ONLY to training data.
# 5. Every training class is increased to at least 300 images.
# 6. Validation and test images remain original.
# ============================================================


# -----------------------------
# PATHS
# -----------------------------

SOURCE = Path(r".\PPLD_extracted\PPLD")
OUTPUT = Path(r".\PPLD_processed")

CLASSES = [
    "Healthy",
    "Leaf_Spot",
    "Leaf_webber",
    "Sterilic_mosaic",
]

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

# Reproducibility
SEED = 42
random.seed(SEED)

# Dataset split
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

# Minimum training images per class
MIN_TRAIN_IMAGES = 300


# ============================================================
# VALIDATION
# ============================================================

if not SOURCE.exists():
    raise FileNotFoundError(
        f"Source dataset not found:\n{SOURCE.resolve()}"
    )

for class_name in CLASSES:
    class_path = SOURCE / class_name

    if not class_path.exists():
        raise FileNotFoundError(
            f"Missing class folder:\n{class_path.resolve()}"
        )


# ============================================================
# COLLECT ORIGINAL IMAGES
# ============================================================

print("\n" + "=" * 70)
print("TUR SATHI AI - PPLD DATASET PREPARATION")
print("=" * 70)

print("\nOriginal dataset:")
print(SOURCE.resolve())

print("\nOutput dataset:")
print(OUTPUT.resolve())

print("\nIMPORTANT:")
print("Original PPLD dataset will NOT be modified.")


all_images = []

for class_name in CLASSES:
    class_dir = SOURCE / class_name

    images = sorted(
        [
            p
            for p in class_dir.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        ]
    )

    for image_path in images:
        all_images.append((class_name, image_path))

    print(f"\n{class_name}: {len(images)} files")


print("\nTotal original image files:", len(all_images))


# ============================================================
# CALCULATE FILE HASHES
# ============================================================

print("\nChecking exact duplicate images...")

hash_to_files = defaultdict(list)

for class_name, image_path in all_images:

    with open(image_path, "rb") as f:
        image_hash = hashlib.md5(f.read()).hexdigest()

    hash_to_files[image_hash].append(
        (class_name, image_path)
    )


# ============================================================
# IDENTIFY CROSS-CLASS DUPLICATES
# ============================================================

cross_class_hashes = set()

for image_hash, files in hash_to_files.items():

    classes_found = set(
        class_name for class_name, _ in files
    )

    if len(classes_found) > 1:
        cross_class_hashes.add(image_hash)


print(
    "Cross-class duplicate groups:",
    len(cross_class_hashes)
)


# ============================================================
# CLEAN DUPLICATES
# ============================================================

# clean_images:
# only one copy of each same-class image
# cross-class conflicting duplicates are completely excluded.

clean_images = []

seen_hashes_per_class = defaultdict(set)

excluded_cross_class = 0
excluded_same_class_duplicate = 0

for class_name, image_path in all_images:

    with open(image_path, "rb") as f:
        image_hash = hashlib.md5(f.read()).hexdigest()

    # --------------------------------------------------------
    # Cross-class duplicate
    # --------------------------------------------------------
    if image_hash in cross_class_hashes:
        excluded_cross_class += 1
        continue

    # --------------------------------------------------------
    # Same-class duplicate
    # --------------------------------------------------------
    if image_hash in seen_hashes_per_class[class_name]:
        excluded_same_class_duplicate += 1
        continue

    seen_hashes_per_class[class_name].add(image_hash)

    clean_images.append(
        (class_name, image_path)
    )


print("\nDuplicate cleaning result:")
print(
    "Excluded cross-class files:",
    excluded_cross_class
)
print(
    "Excluded same-class duplicate files:",
    excluded_same_class_duplicate
)
print(
    "Remaining clean images:",
    len(clean_images)
)


# ============================================================
# CLEAN CLASS COUNTS
# ============================================================

clean_by_class = defaultdict(list)

for class_name, image_path in clean_images:
    clean_by_class[class_name].append(image_path)


print("\nClean dataset class counts:")

for class_name in CLASSES:
    print(
        f"  {class_name:<20} "
        f"{len(clean_by_class[class_name])}"
    )


# ============================================================
# PREPARE OUTPUT DIRECTORY
# ============================================================

if OUTPUT.exists():

    existing_files = list(OUTPUT.rglob("*"))

    if existing_files:
        print("\nExisting PPLD_processed found.")
        print("Removing ONLY the previous generated output...")

        shutil.rmtree(OUTPUT)

OUTPUT.mkdir(parents=True, exist_ok=True)


for split in ["train", "val", "test"]:

    for class_name in CLASSES:

        (OUTPUT / split / class_name).mkdir(
            parents=True,
            exist_ok=True
        )


# ============================================================
# SPLIT DATASET
# ============================================================

print("\nCreating Train / Validation / Test split...")

split_data = {
    "train": defaultdict(list),
    "val": defaultdict(list),
    "test": defaultdict(list),
}


for class_name in CLASSES:

    images = clean_by_class[class_name].copy()

    random.shuffle(images)

    total = len(images)

    train_count = int(total * TRAIN_RATIO)
    val_count = int(total * VAL_RATIO)

    train_images = images[:train_count]

    val_images = images[
        train_count:
        train_count + val_count
    ]

    test_images = images[
        train_count + val_count:
    ]

    split_data["train"][class_name] = train_images
    split_data["val"][class_name] = val_images
    split_data["test"][class_name] = test_images


# ============================================================
# COPY ORIGINAL TRAIN / VAL / TEST IMAGES
# ============================================================

print("\nCopying original images...")

for split in ["train", "val", "test"]:

    for class_name in CLASSES:

        images = split_data[split][class_name]

        for index, source_path in enumerate(images):

            destination = (
                OUTPUT
                / split
                / class_name
                / f"{class_name}_{index:04d}{source_path.suffix.lower()}"
            )

            shutil.copy2(
                source_path,
                destination
            )


# ============================================================
# AUGMENTATION FUNCTION
# ============================================================

def augment_image(image):
    """
    Mild agricultural leaf-image augmentation.

    Only training images are augmented.
    """

    result = image.copy()

    # Random horizontal flip
    if random.random() < 0.5:
        result = ImageOps.mirror(result)

    # Random vertical flip
    if random.random() < 0.15:
        result = ImageOps.flip(result)

    # Small rotation
    angle = random.uniform(-15, 15)

    result = result.rotate(
        angle,
        resample=Image.Resampling.BILINEAR,
        expand=False
    )

    # Brightness
    if random.random() < 0.5:

        factor = random.uniform(0.85, 1.15)

        result = ImageEnhance.Brightness(
            result
        ).enhance(factor)

    # Contrast
    if random.random() < 0.5:

        factor = random.uniform(0.85, 1.15)

        result = ImageEnhance.Contrast(
            result
        ).enhance(factor)

    # Color slightly
    if random.random() < 0.35:

        factor = random.uniform(0.90, 1.10)

        result = ImageEnhance.Color(
            result
        ).enhance(factor)

    return result


# ============================================================
# AUGMENT TRAINING DATA TO MINIMUM 300
# ============================================================

print("\nAugmenting training data...")

for class_name in CLASSES:

    train_dir = OUTPUT / "train" / class_name

    existing_train_images = [
        p
        for p in train_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in IMAGE_EXTENSIONS
    ]

    current_count = len(existing_train_images)

    print(
        f"\n{class_name}: "
        f"original train images = {current_count}"
    )

    if current_count >= MIN_TRAIN_IMAGES:

        print(
            f"Already >= {MIN_TRAIN_IMAGES}. "
            "No augmentation required."
        )

        continue

    required = MIN_TRAIN_IMAGES - current_count

    print(
        f"Generating {required} augmented images..."
    )

    source_pool = existing_train_images.copy()

    for index in range(required):

        source_path = random.choice(source_pool)

        with Image.open(source_path) as img:

            img = img.convert("RGB")

            augmented = augment_image(img)

            output_name = (
                f"{class_name}_aug_{index:04d}.jpg"
            )

            output_path = (
                train_dir / output_name
            )

            augmented.save(
                output_path,
                format="JPEG",
                quality=95
            )


# ============================================================
# FINAL COUNTS
# ============================================================

print("\n" + "=" * 70)
print("FINAL DATASET COUNTS")
print("=" * 70)


for split in ["train", "val", "test"]:

    print(f"\n{split.upper()}")

    split_total = 0

    for class_name in CLASSES:

        class_dir = (
            OUTPUT / split / class_name
        )

        count = len(
            [
                p
                for p in class_dir.iterdir()
                if p.is_file()
                and p.suffix.lower() in IMAGE_EXTENSIONS
            ]
        )

        split_total += count

        print(
            f"  {class_name:<20} {count}"
        )

    print(
        f"  {'TOTAL':<20} {split_total}"
    )


# ============================================================
# FINAL CHECK
# ============================================================

print("\n" + "=" * 70)
print("FINAL CHECK")
print("=" * 70)

success = True

for class_name in CLASSES:

    train_dir = OUTPUT / "train" / class_name

    count = len(
        [
            p
            for p in train_dir.iterdir()
            if p.is_file()
            and p.suffix.lower() in IMAGE_EXTENSIONS
        ]
    )

    if count < MIN_TRAIN_IMAGES:

        success = False

        print(
            f"ERROR: {class_name} has only {count} "
            f"training images."
        )


if success:

    print(
        f"SUCCESS: Every training class has at least "
        f"{MIN_TRAIN_IMAGES} images."
    )

print("\nOriginal dataset was NOT modified.")

print("\nProcessed dataset:")
print(OUTPUT.resolve())

print("\nDataset preparation completed.")
print("=" * 70)