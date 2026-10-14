import os
import shutil
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 1. Setup isolated SQLite DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./comprehensive_test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import models before Base.metadata.create_all
from app.database.models.user import User
from app.database.models.tur_scan import TurScan
from app.database.base import Base

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from app.database.models.user import User
from app.database.models.tur_scan import TurScan

def override_get_current_user():
    db = SessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    db.close()
    return user

# Patch dependencies
from app.main import app
from app.database.session import get_db
from app.api.v1.auth import get_current_user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

# 2. Patch upload directories safely
UPLOAD_DIR = Path("uploads_comprehensive")
UPLOAD_DIR.mkdir(exist_ok=True)

import app.services.storage_service as storage_service
storage_service.UPLOAD_DIR = UPLOAD_DIR
import app.services.prediction_service as prediction_service
prediction_service.UPLOAD_DIR = UPLOAD_DIR

client = TestClient(app)

# 3. Define Test Cases
PROJECT_ROOT = Path("..").resolve()

cases = [
    {
        "id": 1,
        "name": "Healthy (Supported)",
        "path": PROJECT_ROOT / "datasets/pigeonpea_disease_final/test/Healthy/healthy_test_0000.jpg",
        "expected_status": 200
    },
    {
        "id": 2,
        "name": "Leaf Spot (Supported)",
        "path": PROJECT_ROOT / "datasets/pigeonpea_disease_final/test/Leaf_Spot/leaf_spot_test_0000.jpg",
        "expected_status": 200
    },
    {
        "id": 3,
        "name": "Leaf Webber (Supported)",
        "path": PROJECT_ROOT / "datasets/pigeonpea_disease_final/test/Leaf_webber/leaf_webber_test_0000.jpg",
        "expected_status": 200
    },
    {
        "id": 4,
        "name": "Sterility Mosaic (Supported)",
        "path": PROJECT_ROOT / "datasets/pigeonpea_disease_final/test/Sterilic_mosaic/sterilic_mosaic_test_0000.jpg",
        "expected_status": 200
    },
    {
        "id": 5,
        "name": "Wilt (Supported)",
        "path": PROJECT_ROOT / "datasets/pigeonpea_disease_final/test/Wilt/wilt_test_0000.jpg",
        "expected_status": 200
    },
    {
        "id": 6,
        "name": "Alternaria Blight (Unsupported)",
        "path": PROJECT_ROOT / "datasets/new_disease_images/AAlternaria-blight-symptom-on-leaves-and-B-aerial-plant-parts-leaves-stem-buds-and.webp",
        "expected_status": 422
    },
    {
        "id": 7,
        "name": "Unknown Disease (Unsupported)",
        "path": PROJECT_ROOT / "datasets/new_disease_images/488313_0_En_25-1_Fig1_HTML.jpg",
        "expected_status": 422
    },
    {
        "id": 8,
        "name": "Unrelated Crop (Not Tur)",
        "path": PROJECT_ROOT / "datasets/tur_image_validator_v3/test/Not_Tur/10_aug7.jpg",
        "expected_status": 422
    }
]

# Generate invalid file
invalid_path = UPLOAD_DIR / "invalid.jpg"
with open(invalid_path, "wb") as f:
    f.write(b"NOT A REAL IMAGE")
cases.append({
    "id": 9,
    "name": "Corrupted File",
    "path": invalid_path,
    "expected_status": 422
})

# Seed DB
db = SessionLocal()
db.add(User(id=1, email="test@test.com", full_name="Test User"))
db.commit()

for case in cases:
    # copy image if exists
    if not case["path"].exists():
        print(f"SKIPPING {case['id']}: File missing at {case['path']}")
        case["skip"] = True
        continue
    
    case["skip"] = False
    dest_name = f"test_img_{case['id']}.jpg"
    dest_path = UPLOAD_DIR / dest_name
    shutil.copy(case["path"], dest_path)
    
    scan = TurScan(id=case['id'], user_id=1, image_path=dest_name, crop="tur", status="received")
    db.add(scan)
db.commit()
db.close()

# Run Tests
print("-" * 110)
print(f"{'ID':<3} | {'Name':<35} | {'Expected':<8} | {'Actual':<8} | {'Pred Class':<15} | {'Confidence':<10} | {'DB Status'}")
print("-" * 110)

db = SessionLocal()

for case in cases:
    if case.get("skip"):
        print(f"{case['id']:<3} | {case['name']:<35} | {'SKIPPED (File Missing)':<64}")
        continue
        
    scan_id = case['id']
    resp = client.post(f"/api/v1/predictions/tur-leaf/{scan_id}")
    
    actual_status = resp.status_code
    
    # DB Status
    scan = db.query(TurScan).filter(TurScan.id == scan_id).first()
    db_status = scan.status if scan else "missing"
    
    pred_class = "N/A"
    confidence = "N/A"
    
    if actual_status == 200:
        data = resp.json()
        pred_class = data.get("disease_name", "N/A")
        conf = data.get("confidence")
        if conf is not None:
            confidence = f"{conf:.4f}"
    
    print(f"{scan_id:<3} | {case['name']:<35} | {case['expected_status']:<8} | {actual_status:<8} | {pred_class:<15} | {confidence:<10} | {db_status}")

db.close()
print("-" * 110)
