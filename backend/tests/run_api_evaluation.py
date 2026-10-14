import os
import sys
import time
import requests
from pathlib import Path
from collections import defaultdict
from sklearn.metrics import classification_report, confusion_matrix
import concurrent.futures

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REPORT_FILE = PROJECT_ROOT / "backend" / "tests" / "api_evaluation_report.txt"

# Dataset paths
TEST_DIR = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "test"

# Ensure report doesn't exist
if REPORT_FILE.exists():
    print(f"Error: Report file {REPORT_FILE} already exists. Please move or delete it before running this script to avoid overwriting.")
    sys.exit(1)

# Auth payload
AUTH_PAYLOAD = {
    "full_name": "API Evaluator",
    "mobile_number": "8765432109",
    "password": "Password123!",
    "confirm_password": "Password123!"
}

# Supported classes we expect
SUPPORTED_CLASSES = ["Healthy", "Leaf_Spot", "Leaf_webber", "Sterilic_mosaic", "Wilt"]

def get_images():
    """Gathers all images mapped to their true label."""
    image_list = []
    for cls in SUPPORTED_CLASSES:
        cls_dir = TEST_DIR / cls
        if cls_dir.exists():
            for ext in ["*.jpg", "*.jpeg", "*.png"]:
                for p in cls_dir.glob(ext):
                    image_list.append((str(p), cls))
    return image_list

def process_image(img_data, headers):
    img_path, true_label = img_data
    filename = Path(img_path).name
    try:
        with open(img_path, "rb") as f:
            files = {"image": (filename, f, "image/jpeg")}
            data = {"crop": "tur"}
            scan_resp = requests.post(f"{API_BASE_URL}/scans", headers=headers, files=files, data=data)
        
        if scan_resp.status_code != 201:
            return {"status": scan_resp.status_code, "true_label": true_label, "pred_label": "UploadFailed", "rejection": None}
            
        scan_id = scan_resp.json()["scan_id"]
        pred_resp = requests.post(f"{API_BASE_URL}/predictions/tur-leaf/{scan_id}", headers=headers)
        
        if pred_resp.status_code == 200:
            pred_label = pred_resp.json().get("disease_name")
            return {"status": 200, "true_label": true_label, "pred_label": pred_label, "rejection": None}
        elif pred_resp.status_code == 422:
            err_status = pred_resp.json().get("detail", {}).get("status", "unknown_422")
            return {"status": 422, "true_label": true_label, "pred_label": "Rejected", "rejection": err_status}
        else:
            return {"status": pred_resp.status_code, "true_label": true_label, "pred_label": "Failed", "rejection": None}
            
    except Exception as e:
        return {"status": 500, "true_label": true_label, "pred_label": "Failed", "rejection": str(e)}

def main():
    print(f"Starting API Evaluation. Connecting to {API_BASE_URL}...")
    token = None
    try:
        resp = requests.post(f"{API_BASE_URL}/auth/register", json=AUTH_PAYLOAD)
        if resp.status_code == 201:
            token = resp.json()["access_token"]
        elif resp.status_code == 400:
            login_payload = {"identifier": "8765432109", "password": "Password123!"}
            resp = requests.post(f"{API_BASE_URL}/auth/login", json=login_payload)
            resp.raise_for_status()
            token = resp.json()["access_token"]
        else:
            resp.raise_for_status()
    except Exception as e:
        print(f"Failed to authenticate: {e}")
        sys.exit(1)
        
    headers = {"Authorization": f"Bearer {token}"}
    images = get_images()
    print(f"Found {len(images)} images to test.")
    
    y_true = []
    y_pred = []
    rejection_reasons = defaultdict(int)
    
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_image, img, headers) for img in images]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            y_true.append(res["true_label"])
            y_pred.append(res["pred_label"])
            if res["rejection"]:
                rejection_reasons[res["rejection"]] += 1
            completed += 1
            if completed % 10 == 0:
                print(f"Processed {completed}/{len(images)} images...")
                
    total_processed = len(y_true)
    end_to_end_correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    end_to_end_acc = end_to_end_correct / total_processed if total_processed > 0 else 0
    
    classifier_correct = sum(1 for t, p in zip(y_true, y_pred) if t == p and p not in ("Rejected", "UploadFailed", "Failed"))
    total_not_rejected = sum(1 for p in y_pred if p not in ("Rejected", "UploadFailed", "Failed"))
    classifier_acc = classifier_correct / total_not_rejected if total_not_rejected > 0 else 0
    
    report = []
    report.append("="*50)
    report.append("API EVALUATION REPORT - SUPPORTED CLASSES ONLY")
    report.append("="*50)
    report.append(f"Total Images Tested: {total_processed}")
    report.append(f"End-to-End API Accuracy: {end_to_end_acc:.4f} (Includes rejections as failures)")
    report.append(f"Classifier Accuracy: {classifier_acc:.4f} (Excludes rejections)")
    report.append("")
    report.append("--- REJECTIONS (HTTP 422) ---")
    report.append(f"Total Rejected: {sum(rejection_reasons.values())} out of {total_processed}")
    for reason, count in rejection_reasons.items():
        report.append(f"  - {reason}: {count}")
    report.append("")
    report.append("--- CLASSIFICATION METRICS (End-to-End) ---")
    all_labels = SUPPORTED_CLASSES + list(set([p for p in y_pred if p not in SUPPORTED_CLASSES]))
    report.append(classification_report(y_true, y_pred, labels=all_labels, zero_division=0))
    report.append("")
    report.append("--- CONFUSION MATRIX ---")
    report.append("Labels: " + ", ".join(all_labels))
    cm = confusion_matrix(y_true, y_pred, labels=all_labels)
    for row in cm:
        report.append(str(row))
        
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"\nEvaluation Complete. Report saved to: {REPORT_FILE}")

if __name__ == "__main__":
    main()
