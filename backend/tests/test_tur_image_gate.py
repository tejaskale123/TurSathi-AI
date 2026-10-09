import sys
import json
from pathlib import Path

# Add backend directory to sys.path so 'app.' imports work
backend_path = Path("backend").resolve()
sys.path.append(str(backend_path))

from app.ml.tur_image_gate import get_tur_image_gate

def run_test():
    gate = get_tur_image_gate()
    
    test_files = [
        "datasets/tur_image_validator/real_world_test/Tur/realworld_tur_01.png",
        "datasets/tur_image_validator/real_world_test/Not_Tur/realworld_nottur_01.png",
        "datasets/tur_image_validator/real_world_test/Not_Tur/realworld_nottur_02.png"
    ]
    
    print("=" * 60)
    print("TUR IMAGE GATE - ISOLATED TEST")
    print("=" * 60)
    
    for f in test_files:
        path = Path(f)
        print(f"\nTesting: {path.name}")
        
        result = gate.validate(path)
        
        # Format output neatly
        result_dict = {
            "is_valid_tur": result.is_valid_tur,
            "label": result.label,
            "confidence": result.confidence,
            "reason": result.reason,
            "message": result.message
        }
        
        print(json.dumps(result_dict, indent=4))

if __name__ == "__main__":
    run_test()
