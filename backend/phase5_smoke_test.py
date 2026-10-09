import shutil
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database.session import get_db
from app.database.base import Base
from app.database.models.user import User
from app.database.models.tur_scan import TurScan
from app.api.v1.auth import get_current_user

# 1. Setup real Database but separate from dev DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./smoke_test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def override_get_current_user():
    db = SessionLocal()
    user = db.query(User).filter(User.id == 1).first()
    db.close()
    return user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

# 2. Setup Real Images
PROJECT_ROOT = Path("..").resolve()
UPLOAD_DIR = Path("uploads_smoke")
UPLOAD_DIR.mkdir(exist_ok=True)

# We must override the UPLOAD_DIR in the service to point here
import app.services.storage_service
app.services.storage_service.UPLOAD_DIR = UPLOAD_DIR
import app.services.prediction_service
app.services.prediction_service.UPLOAD_DIR = UPLOAD_DIR

def copy_image(src_path, dest_name):
    if not src_path.exists():
        raise FileNotFoundError(f"Source image not found: {src_path}")
    dest_path = UPLOAD_DIR / dest_name
    shutil.copy(src_path, dest_path)
    return dest_name

# Sources
v3_dataset_dir = PROJECT_ROOT / "datasets" / "tur_image_validator_v3" / "test"
realworld_dir = PROJECT_ROOT / "datasets" / "tur_image_validator" / "real_world_test"

# Copy images to mock uploads dir
img1 = copy_image(v3_dataset_dir / "Tur" / "Healthy_0000.jpg", "known_tur.jpg")
img2 = copy_image(v3_dataset_dir / "Not_Tur" / "10_aug7.jpg", "known_nottur.jpg")
img4 = copy_image(realworld_dir / "Tur" / "realworld_tur_01.png", "rw_tur.png")
img5 = copy_image(realworld_dir / "Not_Tur" / "realworld_nottur_01.png", "rw_nottur.png")

# Corrupt Image
img3 = "invalid.jpg"
with open(UPLOAD_DIR / img3, "wb") as f:
    f.write(b"NOT A REAL IMAGE")

# Seed DB
db = SessionLocal()
db.add(User(id=1, email="smoke@test.com", full_name="Smoke Test"))
db.add(TurScan(id=1, user_id=1, image_path=img1, crop="tur", status="received"))
db.add(TurScan(id=2, user_id=1, image_path=img2, crop="tur", status="received"))
db.add(TurScan(id=3, user_id=1, image_path=img3, crop="tur", status="received"))
db.add(TurScan(id=4, user_id=1, image_path=img4, crop="tur", status="received"))
db.add(TurScan(id=5, user_id=1, image_path=img5, crop="tur", status="received"))
db.commit()
db.close()

print("============================================================")
print("PHASE 5I: PRODUCTION SMOKE TEST")
print("============================================================")

def run_test(case_name, scan_id, expected_status):
    print(f"Running {case_name} (Scan {scan_id})...")
    resp = client.post(f"/api/v1/predictions/tur-leaf/{scan_id}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f" -> SUCCESS (200). Disease: {data.get('disease_name')} Confidence: {data.get('confidence')}")
        assert expected_status == 200
    elif resp.status_code == 422:
        data = resp.json()
        print(f" -> REJECTED (422). Message: {data.get('detail', {}).get('message')}")
        assert expected_status == 422
    else:
        print(f" -> ERROR ({resp.status_code}): {resp.text}")
        assert False

# CASE 1: Known Tur (should hit disease model and return 200)
run_test("CASE 1: Known Tur Image", 1, 200)

# CASE 2: Known Not_Tur (should be rejected by gate and return 422)
run_test("CASE 2: Known Not_Tur Image", 2, 422)

# CASE 3: Invalid Image (should be rejected gracefully)
run_test("CASE 3: Invalid Image", 3, 422)

# CASE 4: Known Tur Real-World (should hit disease model)
run_test("CASE 4: Real-World Tur Image", 4, 200)

# CASE 5: Known Not_Tur Real-World (should be rejected by gate)
run_test("CASE 5: Real-World Not_Tur Image", 5, 422)

print("============================================================")
print("ALL SMOKE TESTS PASSED!")
print("============================================================")
