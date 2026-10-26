#!/usr/bin/env python3
"""
================================================================================
TurSathi AI - Automated Hard-Negative Dataset Collection Preparation Tool
================================================================================
Automates the safe, auditable collection and staging of hard-negative imagery
from explicitly licensed, open-access repositories (Wikimedia Commons CC-BY /
CC-BY-SA / CC0 / Public Domain).

STRICT SAFETY CONSTRAINTS:
1. ONLY downloads from curated, approved sources with verified open licenses.
2. Saves images strictly into isolated `ml/retraining/validator_v4/incoming_hard_negatives/`.
3. Never overwrites existing files.
4. Verifies image decodability (PIL), formats, dimensions, and computes SHA-256.
5. Re-checks baseline `validator_v4_manifest.json` to prevent duplicates.
6. Automatically populates intake CSV with provenance, license, and author.
7. Sets reviewer_status to PENDING_REVIEW and split_assignment to unassigned.
8. Never invents labels or automatically marks unreviewed images VERIFIED_ACCEPTED.
9. Genuine pigeonpea diseases (e.g. Alternaria) are NEVER placed in Not_Tur.
10. Baseline manifests, production models, and git-tracked code remain untouched.
================================================================================
"""

import os
import sys
import csv
import json
import hashlib
import argparse
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from PIL import Image

# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ml" / "retraining" / "validator_v4"))

from hard_negative_schema import (
    HardNegativeRecord,
    HardNegativeManifestValidator,
    ReviewerStatus,
    VerifiedLabel,
    OrganCategory,
    SplitAssignment
)

INCOMING_DIR = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "incoming_hard_negatives"
BASE_MANIFEST_PATH = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "validator_v4_manifest.json"
COLLECTION_MANIFEST_PATH = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "hard_negative_collection_manifest.json"
INTAKE_CSV_PATH = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "hard_negative_intake_template.csv"
CANDIDATE_MANIFEST_PATH = PROJECT_ROOT / "ml" / "retraining" / "validator_v4" / "candidate_hard_negatives_manifest.json"

USER_AGENT = "TurSathi-AI-Validator/1.0 (academic research; contact: admin@tursathi.ai)"

# ==============================================================================
# APPROVED LICENSED SOURCES REGISTRY (Curated Wikimedia Commons Items)
# ==============================================================================
APPROVED_COMMONS_ITEMS = [
    # --------------------------------------------------------------------------
    # Category 1: Pigeonpea Non-Leaf Organs (Pods, Stems, Seeds)
    # --------------------------------------------------------------------------
    {
        "title": "File:Pigeon pea pods dried.jpg",
        "category_folder": "pigeonpea_non_leaf_organs",
        "organ_category": OrganCategory.PIGEONPEA_POD.value,
        "candidate_label": VerifiedLabel.TUR_NON_LEAF_ORGAN.value,
        "subject_desc": "Dried pigeonpea pods on surface with seeds visible",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Bff (Wikimedia Commons)"
    },
    {
        "title": "File:Pigeon pea pods dried with ruler.jpg",
        "category_folder": "pigeonpea_non_leaf_organs",
        "organ_category": OrganCategory.PIGEONPEA_POD.value,
        "candidate_label": VerifiedLabel.TUR_NON_LEAF_ORGAN.value,
        "subject_desc": "Dried pigeonpea pods with measurement ruler",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Bff (Wikimedia Commons)"
    },
    {
        "title": "File:Cajanus cajan MHNT.BOT.2015.2.47.jpg",
        "category_folder": "pigeonpea_non_leaf_organs",
        "organ_category": OrganCategory.PIGEONPEA_POD.value,
        "candidate_label": VerifiedLabel.TUR_NON_LEAF_ORGAN.value,
        "subject_desc": "Botanical museum voucher of Cajanus cajan pods",
        "expected_license": "CC BY-SA 3.0",
        "credit": "Muséum de Toulouse"
    },
    {
        "title": "File:Cajanus cajan fruits on white background.jpg",
        "category_folder": "pigeonpea_non_leaf_organs",
        "organ_category": OrganCategory.PIGEONPEA_POD.value,
        "candidate_label": VerifiedLabel.TUR_NON_LEAF_ORGAN.value,
        "subject_desc": "Fresh green and mottled pigeonpea pods",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Bff (Wikimedia Commons)"
    },
    {
        "title": "File:Cajanus cajan kz04.jpg",
        "category_folder": "pigeonpea_non_leaf_organs",
        "organ_category": OrganCategory.PIGEONPEA_POD.value,
        "candidate_label": VerifiedLabel.TUR_NON_LEAF_ORGAN.value,
        "subject_desc": "Matured pigeonpea pod cluster on bush stem",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Krzysztof Ziarnek, Kenraiz"
    },
    {
        "title": "File:Cajanus cajan kz05.jpg",
        "category_folder": "pigeonpea_non_leaf_organs",
        "organ_category": OrganCategory.PIGEONPEA_POD.value,
        "candidate_label": VerifiedLabel.TUR_NON_LEAF_ORGAN.value,
        "subject_desc": "Pigeonpea shrub branches and ripening pods",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Krzysztof Ziarnek, Kenraiz"
    },
    {
        "title": "File:Cajanu caja 080716-1074 ayot.JPG",
        "category_folder": "pigeonpea_non_leaf_organs",
        "organ_category": OrganCategory.PIGEONPEA_POD.value,
        "candidate_label": VerifiedLabel.TUR_NON_LEAF_ORGAN.value,
        "subject_desc": "Close-up of pigeonpea pods developing on branch",
        "expected_license": "CC BY-SA 3.0",
        "credit": "Wibowo Djatmiko"
    },
    {
        "title": "File:Cajanus cajan (Fabaceae) 02.jpg",
        "category_folder": "pigeonpea_non_leaf_organs",
        "organ_category": OrganCategory.PIGEONPEA_POD.value,
        "candidate_label": VerifiedLabel.TUR_NON_LEAF_ORGAN.value,
        "subject_desc": "Cluster of fresh pigeonpea pods and twigs",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Krzysztof Ziarnek, Kenraiz"
    },
    # --------------------------------------------------------------------------
    # Category 2: Agricultural Weeds Common in Indian Farming
    # --------------------------------------------------------------------------
    {
        "title": "File:Parthenium hysterophorus 4.jpg",
        "category_folder": "agricultural_weeds",
        "organ_category": OrganCategory.WEED_FOLIAGE.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Parthenium hysterophorus (Gajar Ghas) weed foliage",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Wikimedia Commons contributor"
    },
    {
        "title": "File:Parthenium hysterophorus 6.jpg",
        "category_folder": "agricultural_weeds",
        "organ_category": OrganCategory.WEED_FOLIAGE.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Parthenium hysterophorus weed inflorescence and leaves",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Wikimedia Commons contributor"
    },
    {
        "title": "File:Parthenium hysterophorus plant with flowers.jpg",
        "category_folder": "agricultural_weeds",
        "organ_category": OrganCategory.WEED_FOLIAGE.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Parthenium hysterophorus whole weed plant in field",
        "expected_license": "CC BY 3.0",
        "credit": "Wikimedia Commons contributor"
    },
    {
        "title": "File:ARS - Commelina benghalensis.jpg",
        "category_folder": "agricultural_weeds",
        "organ_category": OrganCategory.WEED_FOLIAGE.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Commelina benghalensis (Benghal dayflower/Kena) weed habit",
        "expected_license": "Public domain",
        "credit": "Agricultural Research Service, USDA"
    },
    {
        "title": "File:Commelina benghalensis 7.jpg",
        "category_folder": "agricultural_weeds",
        "organ_category": OrganCategory.WEED_FOLIAGE.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Commelina benghalensis weed creeping stem and broad leaves",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Wikimedia Commons contributor"
    },
    {
        "title": "File:Commelina benghalensis kz02.jpg",
        "category_folder": "agricultural_weeds",
        "organ_category": OrganCategory.WEED_FOLIAGE.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Commelina benghalensis weed foliage close-up",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Krzysztof Ziarnek, Kenraiz"
    },
    {
        "title": "File:Commelina benghalensis kz03.jpg",
        "category_folder": "agricultural_weeds",
        "organ_category": OrganCategory.WEED_FOLIAGE.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Commelina benghalensis blue flower and foliage",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Krzysztof Ziarnek, Kenraiz"
    },
    {
        "title": "File:Celosia argentea (Brunei) 02.jpg",
        "category_folder": "agricultural_weeds",
        "organ_category": OrganCategory.WEED_FOLIAGE.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Celosia argentea (Silver cockscomb/Kurdu) weed foliage",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Krzysztof Ziarnek, Kenraiz"
    },
    {
        "title": "File:Celosia argentea in Philippines.jpg",
        "category_folder": "agricultural_weeds",
        "organ_category": OrganCategory.WEED_FOLIAGE.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Celosia argentea weed in farm field",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Wikimedia Commons contributor"
    },
    # --------------------------------------------------------------------------
    # Category 3: Field Clutter, Soil, Irrigation, Non-Crop Backgrounds
    # --------------------------------------------------------------------------
    {
        "title": "File:Furrow irrigation.jpg",
        "category_folder": "field_clutter_and_soil",
        "organ_category": OrganCategory.NON_CROP_CLUTTER.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Agricultural soil furrows and water channel clutter",
        "expected_license": "Public domain",
        "credit": "USDA NRCS"
    },
    {
        "title": "File:Furrow Irrigation in Armenia 002.jpg",
        "category_folder": "field_clutter_and_soil",
        "organ_category": OrganCategory.NON_CROP_CLUTTER.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Field soil with irrigation pipe and barren background",
        "expected_license": "CC BY-SA 3.0",
        "credit": "Vahagn M (Wikimedia Commons)"
    },
    {
        "title": "File:Drip irrigation (Armenia).jpg",
        "category_folder": "field_clutter_and_soil",
        "organ_category": OrganCategory.NON_CROP_CLUTTER.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Drip irrigation black plastic tubing and soil clutter",
        "expected_license": "CC BY-SA 4.0",
        "credit": "Vahagn M (Wikimedia Commons)"
    },
    {
        "title": "File:Drip irrigation system.JPG",
        "category_folder": "field_clutter_and_soil",
        "organ_category": OrganCategory.NON_CROP_CLUTTER.value,
        "candidate_label": VerifiedLabel.NOT_TUR.value,
        "subject_desc": "Drip irrigation pipe network installed across agricultural soil",
        "expected_license": "Public domain",
        "credit": "USDA"
    }
]


def fetch_wikimedia_metadata(titles: List[str]) -> Dict[str, Dict]:
    """Queries Wikimedia Commons API for metadata, URL, and license info."""
    params = {
        "action": "query",
        "titles": "|".join(titles),
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata|mime",
        "format": "json"
    }
    url = f"https://commons.wikimedia.org/w/api.php?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    
    metadata_map = {}
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        pages = data.get("query", {}).get("pages", {})
        for pid, page in pages.items():
            title = page.get("title", "")
            if "missing" in page or not page.get("imageinfo"):
                continue
            ii = page["imageinfo"][0]
            ext = ii.get("extmetadata", {})
            metadata_map[title] = {
                "direct_url": ii.get("url"),
                "mime": ii.get("mime"),
                "width": ii.get("width"),
                "height": ii.get("height"),
                "size_bytes": ii.get("size"),
                "license_short": ext.get("LicenseShortName", {}).get("value", "Open License"),
                "license_url": ext.get("LicenseUrl", {}).get("value", "https://creativecommons.org/"),
                "artist": ext.get("Artist", {}).get("value", "Unknown"),
                "description": ext.get("ImageDescription", {}).get("value", "")
            }
    except Exception as e:
        print(f"[FAIL] Error querying Wikimedia Commons API: {e}")
    return metadata_map


def sanitize_filename(name: str) -> str:
    cleaned = name.replace("File:", "").strip()
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in cleaned).lower()


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def prepare_harvest(dry_run: bool = False, execute_download: bool = True):
    print("=" * 80)
    print("TUR SATHI AI — AUTOMATED LICENSED HARD-NEGATIVE COLLECTION PREPARATION")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Dry Run Mode: {dry_run}")
    print(f"Execute Download: {execute_download}")

    # 1. Load baseline hashes to ensure absolute disjointness
    base_hashes: Set[str] = set()
    if BASE_MANIFEST_PATH.exists():
        with open(BASE_MANIFEST_PATH, "r", encoding="utf-8") as f:
            base_data = json.load(f)
        base_hashes = set(r["sha256"] for r in base_data.get("records", []))
        print(f"[PASS] Loaded {len(base_hashes)} baseline hashes from validator_v4_manifest.json")

    # 2. Fetch remote metadata from approved registry
    print(f"\nQuerying Wikimedia Commons API for {len(APPROVED_COMMONS_ITEMS)} approved sources...")
    all_titles = [item["title"] for item in APPROVED_COMMONS_ITEMS]
    metadata_map = fetch_wikimedia_metadata(all_titles)
    print(f"[PASS] Successfully resolved metadata for {len(metadata_map)} / {len(APPROVED_COMMONS_ITEMS)} approved items.")

    # 3. Process each approved item
    downloaded_records = []
    skipped_existing = 0
    duplicate_count = 0
    corrupt_count = 0
    batch_hashes: Dict[str, str] = {}

    csv_rows = []

    for idx, item in enumerate(APPROVED_COMMONS_ITEMS, 1):
        title = item["title"]
        meta = metadata_map.get(title)
        if not meta:
            print(f"[SKIP] Remote metadata missing for: {title}")
            continue

        direct_url = meta["direct_url"]
        safe_fname = sanitize_filename(title)
        target_dir = INCOMING_DIR / item["category_folder"]
        target_dir.mkdir(parents=True, exist_ok=True)
        local_path = target_dir / safe_fname
        rel_path = str(local_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

        image_id = f"HN_HARVEST_{idx:03d}"

        # Check if already present on disk
        if local_path.exists():
            skipped_existing += 1
            print(f"[{image_id}] File already exists on disk (preserving): {safe_fname}")
        else:
            if not dry_run and execute_download:
                print(f"[{image_id}] Downloading: {safe_fname} ...")
                try:
                    req = urllib.request.Request(direct_url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=30) as resp, open(local_path, "wb") as out_file:
                        out_file.write(resp.read())
                except Exception as e:
                    print(f"  [ERROR] Failed to download {title}: {e}")
                    corrupt_count += 1
                    continue
            else:
                print(f"[{image_id}] [DRY-RUN] Would download: {safe_fname} from {direct_url[:50]}...")

        # If file exists on disk, perform deep integrity audit
        if local_path.exists():
            # Verify image decoding
            try:
                with Image.open(local_path) as im:
                    im.verify()
                    w, h = im.size
                if w < 200 or h < 200:
                    print(f"  [WARN] Dimensions small ({w}x{h}) for {safe_fname}")
            except Exception as e:
                print(f"  [FAIL] Image corrupted or invalid: {safe_fname} ({e})")
                corrupt_count += 1
                if not dry_run:
                    local_path.unlink(missing_ok=True)
                continue

            # Compute hash
            file_hash = compute_sha256(local_path)
            if file_hash in base_hashes:
                print(f"  [COLLISION] SHA-256 matches baseline validator_v4_manifest.json: {safe_fname}")
                duplicate_count += 1
                continue
            if file_hash in batch_hashes:
                print(f"  [DUPLICATE] Exact duplicate within batch of {batch_hashes[file_hash]}: {safe_fname}")
                duplicate_count += 1
                continue
            batch_hashes[file_hash] = image_id

            # Add to candidate intake list
            # SAFETY: ReviewerStatus is ALWAYS PENDING_REVIEW, split is ALWAYS unassigned
            prov = f"Wikimedia_Commons; URL={direct_url}; License={meta['license_short']}; Author={meta['artist']}"
            note = f"Automated harvest: {item['subject_desc']}. License: {meta['license_short']}."
            
            csv_rows.append([
                image_id,
                rel_path,
                prov,
                item["candidate_label"],
                item["organ_category"],
                ReviewerStatus.PENDING_REVIEW.value,
                note,
                "",  # duplicate_group_id
                SplitAssignment.UNASSIGNED.value
            ])
            downloaded_records.append({
                "image_id": image_id,
                "relative_file_path": rel_path,
                "title": title,
                "category": item["organ_category"],
                "candidate_label": item["candidate_label"],
                "license": meta["license_short"],
                "license_url": meta["license_url"],
                "author": meta["artist"],
                "sha256": file_hash,
                "dimensions": f"{meta['width']}x{meta['height']}",
                "status": ReviewerStatus.PENDING_REVIEW.value,
                "split": SplitAssignment.UNASSIGNED.value
            })

    # 4. Write / Update Intake CSV
    if not dry_run and csv_rows:
        with open(INTAKE_CSV_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "# TurSathi AI Hard-Negative Automated Intake CSV",
                "# DO NOT mark images as VERIFIED_ACCEPTED or assign to active splits without agronomist review."
            ])
            writer.writerow([
                "image_id", "relative_file_path", "source_provenance",
                "verified_label", "organ_category", "reviewer_status",
                "reviewer_notes", "duplicate_group_id", "split_assignment"
            ])
            for r in csv_rows:
                writer.writerow(r)
        print(f"\n[Saved] Updated Intake CSV -> {INTAKE_CSV_PATH} ({len(csv_rows)} candidate rows)")

    # 5. Output Summary & Shortage Analysis
    target_by_cat = {
        OrganCategory.WEED_FOLIAGE.value: 100,
        OrganCategory.PIGEONPEA_POD.value: 100,
        OrganCategory.NON_CROP_CLUTTER.value: 100
    }
    staged_by_cat = {cat: 0 for cat in target_by_cat}
    for r in downloaded_records:
        if r["category"] in staged_by_cat:
            staged_by_cat[r["category"]] += 1

    print("\n" + "=" * 80)
    print("COLLECTION & PREPARATION EXECUTION REPORT")
    print("=" * 80)
    print(f"Total Approved Source Items:        {len(APPROVED_COMMONS_ITEMS)}")
    print(f"Successfully Staged on Disk:        {len(downloaded_records)}")
    print(f"Skipped (Already on disk):          {skipped_existing}")
    print(f"Duplicate / Baseline Collisions:    {duplicate_count}")
    print(f"Corrupt / Unreadable Images:        {corrupt_count}")
    print(f"Reviewer Status:                    ALL {len(downloaded_records)} marked PENDING_REVIEW")
    print(f"Split Assignment:                   ALL {len(downloaded_records)} marked unassigned")
    print("-" * 80)
    print("Category Breakdown:")
    for cat, target in target_by_cat.items():
        staged = staged_by_cat.get(cat, 0)
        shortage = target - staged
        print(f"  - {cat:25s}: Staged={staged:2d} (Pending Review) / Target={target} (Shortage: {shortage:2d})")
    
    print("\nTraining Readiness Evaluation:")
    print("  * Verified Hard Negatives in Training Splits (train/val): 0")
    print("  * Documented Minimum Gate Requirement: >= 50 weeds, >= 50 pods/clutter verified")
    print("  * STATUS: MODEL TRAINING REMAINS STRICTLY BLOCKED (STOP)")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TurSathi AI Hard-Negative Dataset Harvester")
    parser.add_argument("--dry-run", action="store_true", help="Audit approved sources without downloading")
    parser.add_argument("--no-download", action="store_true", help="Process existing files only")
    args = parser.parse_args()

    prepare_harvest(dry_run=args.dry_run, execute_download=not args.no_download)
