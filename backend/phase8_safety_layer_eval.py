import sys
import logging
from pathlib import Path
import torch
from PIL import Image
import math
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("phase8_eval")

# Add backend to path so imports work
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.ml.tur_predictor import get_predictor
from app.ml.tur_image_gate import get_tur_image_gate

def calculate_entropy(probs):
    entropy = 0.0
    for p in probs:
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy

def main():
    logger.info("Starting Phase 8 Safety Layer Evaluation (Isolated)")
    
    predictor = get_predictor()
    if not predictor.is_available():
        logger.error("Predictor not available.")
        return
        
    gate = get_tur_image_gate()
    model = predictor._model
    transform = predictor._transform
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    classes = predictor._classes
    
    test_dir = PROJECT_ROOT / "datasets" / "pigeonpea_disease_final" / "test"
    ood_dir = PROJECT_ROOT / "datasets" / "new_disease_images"
    
    if not test_dir.exists():
        logger.error(f"Test dir {test_dir} not found.")
        return
        
    supported_results = []
    unsupported_results = []
    
    def process_image(img_path, true_label):
        try:
            gate_res = gate.validate(img_path)
            gate_conf = gate_res.confidence
            
            image = Image.open(img_path).convert("RGB")
            input_tensor = transform(image).unsqueeze(0).to(device)
            
            with torch.no_grad():
                output = model(input_tensor)
                probabilities = torch.softmax(output, dim=1)[0].cpu().numpy()
            
            sorted_probs = sorted(probabilities, reverse=True)
            top1_conf = sorted_probs[0]
            top2_conf = sorted_probs[1]
            margin = top1_conf - top2_conf
            entropy = calculate_entropy(probabilities)
            
            pred_idx = probabilities.argmax()
            pred_label = classes[pred_idx]
            
            return {
                "true_label": true_label,
                "pred_label": pred_label,
                "gate_conf": gate_conf,
                "top1": top1_conf,
                "margin": margin,
                "entropy": entropy
            }
        except Exception as e:
            logger.error(f"Error processing {img_path}: {e}")
            return None

    logger.info("Processing Supported Test Images...")
    for cls_name in classes:
        cls_dir = test_dir / cls_name
        if not cls_dir.exists(): continue
        for img_path in list(cls_dir.glob("*.jpg")) + list(cls_dir.glob("*.png")):
            res = process_image(img_path, cls_name)
            if res:
                supported_results.append(res)
                
    logger.info("Processing Exploratory Unsupported Images...")
    if ood_dir.exists():
        for img_path in list(ood_dir.glob("*.jpg")) + list(ood_dir.glob("*.jpeg")) + list(ood_dir.glob("*.png")):
            res = process_image(img_path, "Unsupported")
            if res:
                unsupported_results.append(res)
                
    # Evaluate Supported (Baseline Accuracy)
    correct = sum(1 for r in supported_results if r["true_label"] == r["pred_label"])
    total_supp = len(supported_results)
    acc = correct / total_supp if total_supp > 0 else 0
    logger.info(f"--- BASELINE MODEL PERFORMANCE ---")
    logger.info(f"Supported Test Images: {total_supp}")
    logger.info(f"Correct Predictions: {correct}")
    logger.info(f"Overall Accuracy: {acc:.4f}")
    
    # Per-class metrics
    class_metrics = {}
    for c in classes:
        tp = sum(1 for r in supported_results if r["true_label"] == c and r["pred_label"] == c)
        fp = sum(1 for r in supported_results if r["true_label"] != c and r["pred_label"] == c)
        fn = sum(1 for r in supported_results if r["true_label"] == c and r["pred_label"] != c)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        class_metrics[c] = {"Precision": precision, "Recall": recall, "F1": f1, "Support": (tp+fn)}
        logger.info(f"Class {c:15s}: Precision={precision:.4f}, Recall={recall:.4f}, F1={f1:.4f}, Count={tp+fn}")
        
    # Evaluate Thresholds
    logger.info(f"\n--- EVALUATING SAFETY THRESHOLDS ---")
    logger.info(f"Unsupported Images Processed (Exploratory FAR only): {len(unsupported_results)}")
    
    thresholds = [
        {"name": "Current Baseline (Top1 < 0.65)", "check": lambda r: r["top1"] < 0.65},
        {"name": "Strict Top1 (Top1 < 0.85)", "check": lambda r: r["top1"] < 0.85},
        {"name": "Margin Check (Margin < 0.50)", "check": lambda r: r["margin"] < 0.50},
        {"name": "Entropy Check (Entropy > 0.80)", "check": lambda r: r["entropy"] > 0.80},
        {"name": "Gate Check (GateConf < 0.85)", "check": lambda r: r["gate_conf"] < 0.85},
        {"name": "Combined Layer (Top1<0.65 OR Margin<0.4 OR Gate<0.8)", "check": lambda r: (r["top1"] < 0.65) or (r["margin"] < 0.40) or (r["gate_conf"] < 0.80)}
    ]
    
    for t in thresholds:
        name = t["name"]
        check = t["check"]
        
        # FRR: Supported images that get rejected
        frr_count = sum(1 for r in supported_results if check(r))
        frr = frr_count / total_supp if total_supp > 0 else 0
        
        # FAR: Unsupported images that bypass rejection (i.e. accepted)
        far_count = sum(1 for r in unsupported_results if not check(r))
        total_unsupp = len(unsupported_results)
        far = far_count / total_unsupp if total_unsupp > 0 else 0
        
        logger.info(f"Threshold: {name}")
        logger.info(f"  FRR (Supported Rejections): {frr_count}/{total_supp} ({frr:.2%})")
        logger.info(f"  FAR (Unsupported Bypass)  : {far_count}/{total_unsupp} ({far:.2%})")

if __name__ == "__main__":
    main()
