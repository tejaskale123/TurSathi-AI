import os
import sys
import time
import requests
from pathlib import Path
from collections import defaultdict
import concurrent.futures

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REPORT_FILE = PROJECT_ROOT / "backend" / "tests" / "ood_evaluation_report.txt"

# Dataset paths
NOT_TUR_DIR = PROJECT_ROOT / "datasets" / "tur_image_validator_v3" / "test" / "Not_Tur"
NEW_DISEASE_DIR = PROJECT_ROOT / "datasets" / "new_disease_images"

# Ensure report doesn't exist
if REPORT_FILE.exists():
    print(f"Error: Report file {REPORT_FILE} already exists. Please move or delete it before running this script to avoid overwriting.")
    sys.exit(1)

# Auth payload
AUTH_PAYLOAD = {
    "full_name": "OOD Evaluator",
    "mobile_number": "8877665544",
    "password": "Password123!",
    "confirm_password": "Password123!"
}

def get_images(directory, category_name):
    """Gathers all images from a directory."""
    image_list = []
    if directory.exists():
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
            for p in directory.glob(ext):
                image_list.append((str(p), category_name))
    return image_list

def get_mime_type(filename):
    ext = filename.lower().split('.')[-1]
    if ext == 'png': return 'image/png'
    if ext == 'webp': return 'image/webp'
    return 'image/jpeg'

def process_image(img_data, headers):
    img_path, category = img_data
    filename = Path(img_path).name
    mime_type = get_mime_type(filename)
    
    try:
        with open(img_path, "rb") as f:
            files = {"image": (filename, f, mime_type)}
            data = {"crop": "tur"}
            scan_resp = requests.post(f"{API_BASE_URL}/scans", headers=headers, files=files, data=data)
        
        if scan_resp.status_code != 201:
            return {"outcome": "UploadFailed", "status": scan_resp.status_code, "category": category, "pred_label": None, "confidence": None, "path": img_path}
            
        scan_id = scan_resp.json()["scan_id"]
        pred_resp = requests.post(f"{API_BASE_URL}/predictions/tur-leaf/{scan_id}", headers=headers)
        
        if pred_resp.status_code == 200:
            pred_json = pred_resp.json()
            return {
                "outcome": "Accepted", 
                "status": 200, 
                "category": category, 
                "pred_label": pred_json.get("disease_name"), 
                "confidence": pred_json.get("confidence"), 
                "path": img_path
            }
        elif pred_resp.status_code == 422:
            err_status = pred_resp.json().get("detail", {}).get("status", "unknown_422")
            if err_status == "validation_failed":
                return {"outcome": "GateRejection", "status": 422, "category": category, "pred_label": None, "confidence": None, "path": img_path}
            elif err_status == "unsupported_disease":
                return {"outcome": "ConfidenceRejection", "status": 422, "category": category, "pred_label": None, "confidence": None, "path": img_path}
            else:
                return {"outcome": f"Other422_{err_status}", "status": 422, "category": category, "pred_label": None, "confidence": None, "path": img_path}
        elif pred_resp.status_code == 503:
            return {"outcome": "ModelNotConfigured", "status": 503, "category": category, "pred_label": None, "confidence": None, "path": img_path}
        else:
            return {"outcome": "UnexpectedHTTPStatus", "status": pred_resp.status_code, "category": category, "pred_label": None, "confidence": None, "path": img_path}
            
    except Exception as e:
        return {"outcome": "ExecutionError", "status": 500, "category": category, "pred_label": str(e), "confidence": None, "path": img_path}

def main():
    print(f"Starting OOD API Evaluation. Connecting to {API_BASE_URL}...")
    token = None
    try:
        resp = requests.post(f"{API_BASE_URL}/auth/register", json=AUTH_PAYLOAD)
        if resp.status_code == 201:
            token = resp.json()["access_token"]
        elif resp.status_code == 400:
            login_payload = {"identifier": AUTH_PAYLOAD["mobile_number"], "password": AUTH_PAYLOAD["password"]}
            resp = requests.post(f"{API_BASE_URL}/auth/login", json=login_payload)
            resp.raise_for_status()
            token = resp.json()["access_token"]
        else:
            resp.raise_for_status()
    except Exception as e:
        print(f"Failed to authenticate: {e}")
        sys.exit(1)
        
    headers = {"Authorization": f"Bearer {token}"}
    
    not_tur_images = get_images(NOT_TUR_DIR, "Verified_Not_Tur")
    new_disease_images = get_images(NEW_DISEASE_DIR, "Unverified_Unsupported_Disease")
    
    all_images = not_tur_images + new_disease_images
    print(f"Found {len(not_tur_images)} Verified Not_Tur images.")
    print(f"Found {len(new_disease_images)} Unverified Unsupported Disease images.")
    print(f"Total to evaluate: {len(all_images)}")
    
    results = []
    
    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(process_image, img, headers) for img in all_images]
        for future in concurrent.futures.as_completed(futures):
            results.append(future.result())
            completed += 1
            if completed % 10 == 0:
                print(f"Processed {completed}/{len(all_images)} images...")
                
    report = []
    report.append("="*50)
    report.append("STAGE 2: OUT-OF-DISTRIBUTION (OOD) EVALUATION REPORT")
    report.append("="*50)
    
    # Analyze Verified Not_Tur
    report.append("\n--- VERIFIED NOT_TUR IMAGES ---")
    nt_results = [r for r in results if r["category"] == "Verified_Not_Tur"]
    nt_total = len(nt_results)
    
    nt_gate = sum(1 for r in nt_results if r["outcome"] == "GateRejection")
    nt_conf = sum(1 for r in nt_results if r["outcome"] == "ConfidenceRejection")
    nt_acc = sum(1 for r in nt_results if r["outcome"] == "Accepted")
    nt_fail = sum(1 for r in nt_results if r["outcome"] not in ("GateRejection", "ConfidenceRejection", "Accepted"))
    
    report.append(f"Total Evaluated: {nt_total}")
    report.append(f"Correctly Rejected by Gate (validation_failed): {nt_gate} ({(nt_gate/nt_total)*100 if nt_total else 0:.1f}%)")
    report.append(f"Rejected by Confidence (unsupported_disease): {nt_conf}")
    report.append(f"Confirmed False Acceptance (FAR / High-Confidence Incorrect): {nt_acc} ({(nt_acc/nt_total)*100 if nt_total else 0:.1f}%)")
    report.append(f"Errors (Upload/503/Other): {nt_fail}")
    
    # Analyze Unverified Unsupported Diseases
    report.append("\n--- UNVERIFIED UNSUPPORTED TUR DISEASES ---")
    ud_results = [r for r in results if r["category"] == "Unverified_Unsupported_Disease"]
    ud_total = len(ud_results)
    
    ud_gate = sum(1 for r in ud_results if r["outcome"] == "GateRejection")
    ud_conf = sum(1 for r in ud_results if r["outcome"] == "ConfidenceRejection")
    ud_acc = sum(1 for r in ud_results if r["outcome"] == "Accepted")
    ud_fail = sum(1 for r in ud_results if r["outcome"] not in ("GateRejection", "ConfidenceRejection", "Accepted"))
    
    report.append(f"Total Evaluated: {ud_total}")
    report.append(f"Rejected by Gate (validation_failed): {ud_gate}")
    report.append(f"Rejected by Confidence (unsupported_disease): {ud_conf} ({(ud_conf/ud_total)*100 if ud_total else 0:.1f}%)")
    report.append(f"Exploratory Acceptance (Unknown if correct/incorrect): {ud_acc} ({(ud_acc/ud_total)*100 if ud_total else 0:.1f}%)")
    report.append(f"Errors (Upload/503/Other): {ud_fail}")
    
    report.append("\n--- ACCEPTED IMAGES BREAKDOWN ---")
    accepted_cases = [r for r in results if r["outcome"] == "Accepted"]
    if not accepted_cases:
        report.append("None. The safety gates successfully blocked all OOD images.")
    else:
        for r in accepted_cases:
            label_type = "Confirmed False Acceptance" if r["category"] == "Verified_Not_Tur" else "Exploratory Acceptance"
            report.append(f"[{label_type}] Pred: {r['pred_label']} (Conf: {r['confidence']}) | File: {Path(r['path']).name}")
            
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print(f"\nEvaluation Complete. Report saved to: {REPORT_FILE}")

if __name__ == "__main__":
    main()
