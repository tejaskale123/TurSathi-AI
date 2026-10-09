import os
import json

def compare_versions():
    print("=" * 80)
    print("PHASE 4M: V1 vs V2 vs V3 COMPARISON")
    print("=" * 80)
    
    # Established V1 and V2 results
    v1 = {
        "model": "V1",
        "train_size": "2,460 (Square)",
        "internal_acc": "N/A",
        "rw_acc": 55.0,
        "rw_tur_acc": 18.18,
        "rw_not_tur_acc": 100.0,
        "tur_recall": 18.18,
        "not_tur_recall": 100.0,
        "false_accepts": 0,
        "false_rejects": 9
    }
    
    v2 = {
        "model": "V2",
        "train_size": "2,920 (Square)",
        "internal_acc": 100.0,
        "rw_acc": 50.0,
        "rw_tur_acc": 18.18,
        "rw_not_tur_acc": 100.0,
        "tur_recall": 18.18,
        "not_tur_recall": 100.0,
        "false_accepts": 0,
        "false_rejects": 9
    }
    
    # Load V3 results
    try:
        with open("v3_realworld_holdout_results.json", "r") as f:
            v3_results = json.load(f)
            
        tur_total = sum(1 for r in v3_results if r["actual"] == "Tur")
        tur_correct = sum(1 for r in v3_results if r["actual"] == "Tur" and r["correct"])
        not_tur_total = sum(1 for r in v3_results if r["actual"] == "Not_Tur")
        not_tur_correct = sum(1 for r in v3_results if r["actual"] == "Not_Tur" and r["correct"])
        
        total = tur_total + not_tur_total
        correct = tur_correct + not_tur_correct
        
        v3 = {
            "model": "V3",
            "train_size": "3,041 (Square/Portrait/Landscape)",
            "internal_acc": 0.0, # Filled manually or parsed, but we assume it's high
            "rw_acc": (correct / total) * 100 if total > 0 else 0,
            "rw_tur_acc": (tur_correct / tur_total) * 100 if tur_total > 0 else 0,
            "rw_not_tur_acc": (not_tur_correct / not_tur_total) * 100 if not_tur_total > 0 else 0,
            "tur_recall": (tur_correct / tur_total) * 100 if tur_total > 0 else 0,
            "not_tur_recall": (not_tur_correct / not_tur_total) * 100 if not_tur_total > 0 else 0,
            "false_accepts": not_tur_total - not_tur_correct,
            "false_rejects": tur_total - tur_correct
        }
    except Exception as e:
        print(f"Error loading V3 results: {e}")
        return
        
    try:
        with open("v3_internal_test_report.txt", "r") as f:
            for line in f:
                if "Accuracy               :" in line:
                    v3["internal_acc"] = float(line.split(":")[1].strip()) * 100
    except Exception:
        pass
        
    # Generate Report
    report = []
    report.append("============================================================")
    report.append("VALIDATOR V1 vs V2 vs V3 COMPARISON")
    report.append("============================================================")
    
    header = f"{'Metric':<30} | {'V1':<15} | {'V2':<15} | {'V3':<15}"
    report.append(header)
    report.append("-" * len(header))
    
    def format_row(metric, key):
        v1_val = v1[key] if isinstance(v1[key], str) else f"{v1[key]:.2f}%" if "acc" in key or "recall" in key else str(v1[key])
        v2_val = v2[key] if isinstance(v2[key], str) else f"{v2[key]:.2f}%" if "acc" in key or "recall" in key else str(v2[key])
        v3_val = v3[key] if isinstance(v3[key], str) else f"{v3[key]:.2f}%" if "acc" in key or "recall" in key else str(v3[key])
        return f"{metric:<30} | {v1_val:<15} | {v2_val:<15} | {v3_val:<15}"
        
    report.append(format_row("Training Dataset Size", "train_size"))
    report.append(format_row("Internal Test Accuracy", "internal_acc"))
    report.append(format_row("Real-World Total Accuracy", "rw_acc"))
    report.append(format_row("Real-World Tur Accuracy", "rw_tur_acc"))
    report.append(format_row("Real-World Not_Tur Accuracy", "rw_not_tur_acc"))
    report.append(format_row("Tur Recall", "tur_recall"))
    report.append(format_row("Not_Tur Recall", "not_tur_recall"))
    report.append(format_row("False Acceptance Count", "false_accepts"))
    report.append(format_row("False Rejection Count", "false_rejects"))
    
    report.append("\n============================================================")
    report.append("ANALYSIS")
    report.append("============================================================")
    
    report.append("1. Did V3 improve real-world Tur recognition?")
    if v3["tur_recall"] > v2["tur_recall"]:
        report.append(f"   Yes. Tur recall improved from {v2['tur_recall']:.2f}% to {v3['tur_recall']:.2f}%.")
    else:
        report.append(f"   No. Tur recall went from {v2['tur_recall']:.2f}% to {v3['tur_recall']:.2f}%.")
        
    report.append("2. Did V3 improve total real-world accuracy?")
    if v3["rw_acc"] > max(v1["rw_acc"], v2["rw_acc"]):
        report.append(f"   Yes. Total accuracy is now {v3['rw_acc']:.2f}%.")
    else:
        report.append(f"   No. Total accuracy is {v3['rw_acc']:.2f}%.")
        
    report.append("3. Did V3 reduce false rejection of real Tur images?")
    if v3["false_rejects"] < v2["false_rejects"]:
        report.append(f"   Yes. False rejections decreased from {v2['false_rejects']} to {v3['false_rejects']}.")
    else:
        report.append(f"   No. False rejections went from {v2['false_rejects']} to {v3['false_rejects']}.")
        
    report.append("4. Did V3 introduce any increase in false acceptance?")
    if v3["false_accepts"] > v2["false_accepts"]:
        report.append(f"   Yes. False accepts increased from {v2['false_accepts']} to {v3['false_accepts']}.")
    else:
        report.append(f"   No. False accepts remained at {v3['false_accepts']}.")
        
    report.append("5. Is V3 clearly better than V1?")
    if v3["rw_acc"] > v1["rw_acc"] and v3["tur_recall"] > v1["tur_recall"]:
        report.append("   Yes, on the real-world holdout V3 outperforms V1 significantly.")
    else:
        report.append("   No, V3 does not clearly outperform V1 on the holdout.")
        
    report.append("6. Is V3 clearly better than V2?")
    if v3["rw_acc"] > v2["rw_acc"] and v3["tur_recall"] > v2["tur_recall"]:
        report.append("   Yes, V3 overcomes the domain gap that crippled V2.")
    else:
        report.append("   No, V3 does not clearly outperform V2.")
        
    report_text = "\n".join(report)
    print(report_text)
    
    with open("validator_v1_v2_v3_comparison.txt", "w", encoding="utf-8") as f:
        f.write(report_text)

if __name__ == "__main__":
    compare_versions()
