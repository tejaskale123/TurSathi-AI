# -*- coding: utf-8 -*-
"""
TurSathi AI - Balanced Pigeonpea Disease Dataset Preparation
Target: 500 images/class  (train=300, val=100, test=100)
Author: TurSathi AI Dataset Pipeline  |  Date: 2026-10-04
"""
import sys, os, shutil, hashlib, random, traceback
from pathlib import Path
from PIL import Image

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

RANDOM_SEED      = 42
PROJECT_ROOT     = Path(__file__).resolve().parent.parent
OUTPUT_DIR       = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final"
STAGING_DIR      = PROJECT_ROOT / "datasets" / "_staging"  # temp pool per class
CLASSES          = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]
TARGET_PER_CLASS = 500
TARGET_TRAIN     = 300
TARGET_VAL       = 100
TARGET_TEST      = 100
SPLITS           = ["train", "val", "test"]
VALID_EXT        = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}

# External source directories (never cleared by this script)
EXTERNAL_SOURCES = {
    "Healthy": [
        PROJECT_ROOT / "PPLD_processed" / "train" / "Healthy",
        PROJECT_ROOT / "PPLD_processed" / "val"   / "Healthy",
        PROJECT_ROOT / "PPLD_processed" / "test"  / "Healthy",
        PROJECT_ROOT / "PPLD_extracted" / "PPLD_backup_before_duplicate_removal" / "Healthy",
        PROJECT_ROOT / "PPLD_extracted" / "PPLD"  / "Healthy",
    ],
    "Leaf_Spot": [
        PROJECT_ROOT / "PPLD_processed" / "train" / "Leaf_Spot",
        PROJECT_ROOT / "PPLD_processed" / "val"   / "Leaf_Spot",
        PROJECT_ROOT / "PPLD_processed" / "test"  / "Leaf_Spot",
        PROJECT_ROOT / "PPLD_extracted" / "PPLD_backup_before_duplicate_removal" / "Leaf_Spot",
        PROJECT_ROOT / "PPLD_extracted" / "PPLD"  / "Leaf_Spot",
    ],
    "Leaf_webber": [
        PROJECT_ROOT / "PPLD_processed" / "train" / "Leaf_webber",
        PROJECT_ROOT / "PPLD_processed" / "val"   / "Leaf_webber",
        PROJECT_ROOT / "PPLD_processed" / "test"  / "Leaf_webber",
        PROJECT_ROOT / "PPLD_extracted" / "PPLD_backup_before_duplicate_removal" / "Leaf_webber",
        PROJECT_ROOT / "PPLD_extracted" / "PPLD"  / "Leaf_webber",
    ],
    "Sterilic_mosaic": [
        PROJECT_ROOT / "PPLD_processed" / "train" / "Sterilic_mosaic",
        PROJECT_ROOT / "PPLD_processed" / "val"   / "Sterilic_mosaic",
        PROJECT_ROOT / "PPLD_processed" / "test"  / "Sterilic_mosaic",
        PROJECT_ROOT / "PPLD_extracted" / "PPLD_backup_before_duplicate_removal" / "Sterilic_mosaic",
        PROJECT_ROOT / "PPLD_extracted" / "PPLD"  / "Sterilic_mosaic",
    ],
    "Wilt": [],  # No external Wilt source - only what's in OUTPUT_DIR
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_valid_image(path):
    try:
        with Image.open(str(path)) as img:
            img.verify()
        with Image.open(str(path)) as img:
            img.load()
        return True
    except Exception:
        return False


def collect_from_dirs(dirs):
    imgs = []
    for d in dirs:
        d = Path(d)
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix.lower() in VALID_EXT:
                imgs.append(f)
    return imgs


def dedup(images):
    seen, unique, dupes = set(), [], 0
    for img in images:
        h = sha256_file(img)
        if h not in seen:
            seen.add(h); unique.append(img)
        else:
            dupes += 1
    print(f"    Dedup: {len(images)} -> {len(unique)} unique ({dupes} removed)")
    return unique


def verify(images):
    valid, bad = [], []
    for img in images:
        (valid if is_valid_image(img) else bad).append(img)
    if bad:
        print(f"    WARNING: {len(bad)} corrupted images skipped")
    return valid, bad


def copy_to(imgs, out_dir, prefix, split_name):
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, src in enumerate(imgs):
        ext = Path(src).suffix.lower()
        shutil.copy2(str(src), str(out_dir / f"{prefix}_{split_name}_{i:04d}{ext}"))


def main():
    random.seed(RANDOM_SEED)
    print("=" * 70)
    print("TurSathi AI - Balanced Dataset Preparation")
    print("=" * 70)
    print(f"Root   : {PROJECT_ROOT}")
    print(f"Output : {OUTPUT_DIR}")
    print(f"Target : {TARGET_PER_CLASS}/class (train={TARGET_TRAIN}, val={TARGET_VAL}, test={TARGET_TEST})")
    print(f"Seed   : {RANDOM_SEED}")
    print()

    # ── STEP 0: Stage ALL current output images to safe temp dirs ───────────
    # This prevents the "source deleted before copy" bug.
    print("STEP 0: Staging current output images to safe temp folders...")
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True)

    staged_per_class = {}
    for cls in CLASSES:
        cls_stage = STAGING_DIR / cls
        cls_stage.mkdir()
        count = 0
        for split in SPLITS:
            src_dir = OUTPUT_DIR / split / cls
            if not src_dir.exists():
                continue
            for f in sorted(src_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in VALID_EXT:
                    # Unique name: split_originalname
                    dst = cls_stage / f"{split}_{f.name}"
                    shutil.copy2(str(f), str(dst))
                    count += 1
        staged_per_class[cls] = count
        print(f"  {cls}: staged {count} images")
    print()

    shortage_report = {}
    class_results   = {}

    for cls in CLASSES:
        print("-" * 70)
        print(f"  CLASS: {cls}")
        print("-" * 70)

        # Sources = staged output + external sources
        all_source_dirs = [STAGING_DIR / cls] + EXTERNAL_SOURCES.get(cls, [])
        candidates = collect_from_dirs(all_source_dirs)
        print(f"  [1] Raw candidates : {len(candidates)}")

        print("  [2] Verifying...")
        valid, bad = verify(candidates)
        print(f"      Valid={len(valid)}  Corrupted={len(bad)}")

        print("  [3] Deduplicating...")
        unique = dedup(valid)
        print(f"      Unique: {len(unique)}")

        if len(unique) < TARGET_PER_CLASS:
            shortage = TARGET_PER_CLASS - len(unique)
            shortage_report[cls] = {
                "available": len(unique),
                "target": TARGET_PER_CLASS,
                "shortage": shortage,
            }
            print(f"\n  *** SHORTAGE: {cls} = {len(unique)}/{TARGET_PER_CLASS} (need {shortage} more) ***")
            usable = len(unique)
            n_train = int(usable * 0.60)
            n_val   = int(usable * 0.20)
            n_test  = usable - n_train - n_val
        else:
            usable = TARGET_PER_CLASS
            n_train, n_val, n_test = TARGET_TRAIN, TARGET_VAL, TARGET_TEST
            print(f"  OK: Using {usable} of {len(unique)} available.")

        random.seed(RANDOM_SEED)
        random.shuffle(unique)
        selected = unique[:usable]
        train_imgs = selected[:n_train]
        val_imgs   = selected[n_train: n_train + n_val]
        test_imgs  = selected[n_train + n_val:]
        print(f"  [4] Split: train={len(train_imgs)}, val={len(val_imgs)}, test={len(test_imgs)}")

        # Clear & rebuild output
        prefix = cls.lower()
        out = {sp: OUTPUT_DIR / sp / cls for sp in SPLITS}
        for d in out.values():
            if d.exists(): shutil.rmtree(d)
            d.mkdir(parents=True)

        copy_to(train_imgs, out["train"], prefix, "train")
        copy_to(val_imgs,   out["val"],   prefix, "val")
        copy_to(test_imgs,  out["test"],  prefix, "test")

        a = {sp: len(list(out[sp].iterdir())) for sp in SPLITS}
        a["total"] = sum(a.values())
        class_results[cls] = a
        print(f"  DONE: train={a['train']}, val={a['val']}, test={a['test']}, total={a['total']}")
        print()

    # Cleanup staging
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    print("Staging temp cleaned up.")
    print()

    # ── Cross-split leakage check ─────────────────────────────────────────────
    print("=" * 70)
    print("CROSS-SPLIT LEAKAGE CHECK (SHA256)")
    print("=" * 70)
    leakage = False
    for cls in CLASSES:
        hashes = {sp: set() for sp in SPLITS}
        for sp in SPLITS:
            d = OUTPUT_DIR / sp / cls
            if d.exists():
                for f in d.iterdir():
                    if f.is_file():
                        hashes[sp].add(sha256_file(f))
        tv = hashes["train"] & hashes["val"]
        tt = hashes["train"] & hashes["test"]
        vt = hashes["val"]   & hashes["test"]
        if tv or tt or vt:
            leakage = True
            print(f"  FAIL {cls}: tv={len(tv)}, tt={len(tt)}, vt={len(vt)}")
        else:
            print(f"  OK   {cls}: No leakage")

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("FINAL DATASET SUMMARY")
    print("=" * 70)
    print(f"{'Class':<20} {'Train':>6} {'Val':>6} {'Test':>6} {'Total':>7}  Status")
    print("-" * 60)
    gt = gv = gte = gtotal = 0
    for cls in CLASSES:
        r  = class_results.get(cls, {sp:0 for sp in SPLITS+["total"]})
        ok = (r["train"]==TARGET_TRAIN and r["val"]==TARGET_VAL and r["test"]==TARGET_TEST)
        print(f"{cls:<20} {r['train']:>6} {r['val']:>6} {r['test']:>6} {r['total']:>7}  {'OK' if ok else 'SHORTAGE'}")
        gt += r["train"]; gv += r["val"]; gte += r["test"]; gtotal += r["total"]
    print("-" * 60)
    print(f"{'TOTAL':<20} {gt:>6} {gv:>6} {gte:>6} {gtotal:>7}")
    print(f"\nExpected: {TARGET_TRAIN*5} / {TARGET_VAL*5} / {TARGET_TEST*5} / {TARGET_PER_CLASS*5}")

    # ── Shortage report ───────────────────────────────────────────────────────
    if shortage_report:
        print()
        print("=" * 70)
        print("SHORTAGE REPORT")
        print("=" * 70)
        for cls, info in shortage_report.items():
            print(f"  {cls}: available={info['available']}, shortage={info['shortage']}")
            print(f"    --> Collect {info['shortage']} more verified '{cls}' images and rerun.")
        print()
        print("  *** DO NOT TRAIN -- dataset is IMBALANCED. ***")
    else:
        print("\n  ALL CLASSES BALANCED (500 each). Dataset READY.")

    # ── Validation checks ─────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("VALIDATION CHECKS")
    print("=" * 70)
    passed = total_c = 0

    def chk(label, cond):
        nonlocal passed, total_c
        total_c += 1
        mark = "PASS" if cond else "FAIL"
        print(f"  [{mark}] {label}")
        if cond: passed += 1

    chk("Grand total correct or shortage reported",
        gtotal == TARGET_PER_CLASS * 5 or bool(shortage_report))
    chk("No cross-split leakage", not leakage)
    chk("All 5 classes processed", len(class_results) == 5)
    for sp in SPLITS:
        for cls in CLASSES:
            d = OUTPUT_DIR / sp / cls
            chk(f"Folder exists: {sp}/{cls}", d.exists())
            if d.exists() and cls not in shortage_report:
                count = len([f for f in d.iterdir() if f.is_file()])
                tgt = TARGET_TRAIN if sp=="train" else TARGET_VAL if sp=="val" else TARGET_TEST
                chk(f"Count correct: {sp}/{cls} ({count}/{tgt})", count == tgt)

    print(f"\n  Checks: {passed}/{total_c} passed")
    print()
    if shortage_report:
        print("INCOMPLETE -- Resolve shortages before training.")
        sys.exit(1)
    else:
        print("COMPLETE -- All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(2)
    except Exception as e:
        print(f"\nFATAL: {e}")
        traceback.print_exc()
        sys.exit(3)
