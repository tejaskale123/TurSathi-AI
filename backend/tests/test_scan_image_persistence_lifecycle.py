"""
Focused Test Suite for Phase G1: Scan Image Persistence Lifecycle & Rollback Hardening.

Covers:
1. Successful scan creation: image is persisted to disk, TurScan record is created, image_path matches.
2. Database commit failure: session is rolled back, the newly created image file is deleted from disk, HTTP 500 raised.
3. Pre-existing unrelated image files in uploads/scans/ are strictly preserved when another scan creation fails.
4. Image file cleanup failure (e.g. disk permission error) does not mask the original database exception.
5. Existing upload validation guards (empty file, invalid MIME, oversized image) reject before file or DB operations.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.models.tur_scan import TurScan
from app.database.models.user import User
import app.services.storage_service as storage_module
from app.services.scan_service import create_scan_with_image


TINY_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
    b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
    b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
    b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
    b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4"
    b"\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
    b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)


@pytest.fixture(scope="function")
def isolated_storage_and_db(monkeypatch):
    """
    Sets up an in-memory SQLite database and an isolated temporary upload directory.
    Guarantees zero writes or file operations in the production backend/uploads/ folder.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        monkeypatch.setattr(storage_module, "UPLOAD_DIR", temp_path)
        monkeypatch.setattr(storage_module, "SCAN_IMAGES_DIR", temp_path / "scans")
        monkeypatch.setattr(storage_module, "VOICE_REPORTS_DIR", temp_path / "voice_reports")

        session = TestingSessionLocal()
        try:
            # Seed test user
            user = User(
                id=1,
                full_name="Farmer Suresh",
                mobile_number="9876543211",
                password_hash="hashed_pw",
                is_active=True,
            )
            session.add(user)
            session.commit()

            yield session, temp_path
        finally:
            session.close()
            Base.metadata.drop_all(bind=engine)
            engine.dispose()


def test_scan_creation_success_persists_image_and_record(isolated_storage_and_db):
    """
    Verifies that on successful scan creation:
    1. The image is written to the isolated scans/ directory.
    2. The TurScan database record is created with matching image_path.
    3. Status is 'received' and prediction_status is 'pending'.
    """
    db, upload_root = isolated_storage_and_db

    scan = create_scan_with_image(
        db=db,
        user_id=1,
        file_bytes=TINY_JPEG_BYTES,
        content_type="image/jpeg",
        original_filename="healthy_leaf.jpg",
        crop="tur",
    )

    assert scan.id is not None
    assert scan.user_id == 1
    assert scan.crop == "tur"
    assert scan.status == "received"
    assert scan.prediction_status == "pending"
    assert scan.image_filename == "healthy_leaf.jpg"
    assert scan.image_size == len(TINY_JPEG_BYTES)

    # Check file exists on disk
    expected_disk_file = upload_root / scan.image_path
    assert expected_disk_file.is_file(), f"Expected image file at {expected_disk_file} does not exist"
    assert expected_disk_file.read_bytes() == TINY_JPEG_BYTES


def test_scan_creation_db_commit_failure_rolls_back_and_cleans_up_image(isolated_storage_and_db, monkeypatch):
    """
    Verifies that when database commit fails during scan creation:
    1. db.rollback() is invoked.
    2. The newly written image file on disk is removed.
    3. HTTP 500 is raised.
    4. No scan record remains in the database.
    """
    db, upload_root = isolated_storage_and_db

    scans_dir = upload_root / "scans"
    scans_dir.mkdir(parents=True, exist_ok=True)

    # Mock db.commit to simulate database failure
    def mock_commit():
        raise RuntimeError("Simulated database deadlock / disk full error")

    monkeypatch.setattr(db, "commit", mock_commit)

    with pytest.raises(HTTPException) as exc_info:
        create_scan_with_image(
            db=db,
            user_id=1,
            file_bytes=TINY_JPEG_BYTES,
            content_type="image/jpeg",
            original_filename="deadlock_test.jpg",
            crop="tur",
        )

    assert exc_info.value.status_code == 500
    assert "Scan record could not be saved" in exc_info.value.detail

    # Verify no files remain in scans_dir (the newly created image was cleaned up)
    remaining_files = list(scans_dir.iterdir())
    assert len(remaining_files) == 0, f"Expected 0 orphaned files, found: {remaining_files}"

    # Verify database has zero scans
    assert db.query(TurScan).count() == 0


def test_scan_creation_db_failure_preserves_existing_unrelated_images(isolated_storage_and_db, monkeypatch):
    """
    Verifies that when a scan creation fails and cleans up its own image,
    pre-existing unrelated image files in scans/ are strictly untouched.
    """
    db, upload_root = isolated_storage_and_db
    scans_dir = upload_root / "scans"
    scans_dir.mkdir(parents=True, exist_ok=True)

    # Create pre-existing image file
    pre_existing_file = scans_dir / "pre_existing_scan_123.jpg"
    pre_existing_bytes = b"PRE_EXISTING_SCAN_BINARY_DATA"
    pre_existing_file.write_bytes(pre_existing_bytes)

    # Mock db.commit to fail
    def mock_commit():
        raise RuntimeError("Simulated database constraint violation")

    monkeypatch.setattr(db, "commit", mock_commit)

    with pytest.raises(HTTPException) as exc_info:
        create_scan_with_image(
            db=db,
            user_id=1,
            file_bytes=TINY_JPEG_BYTES,
            content_type="image/jpeg",
            original_filename="failed_leaf.jpg",
            crop="tur",
        )

    assert exc_info.value.status_code == 500

    # Assert pre-existing file is intact and unchanged
    assert pre_existing_file.is_file(), "Pre-existing image file was erroneously deleted!"
    assert pre_existing_file.read_bytes() == pre_existing_bytes

    # Assert no other file was created
    all_files = list(scans_dir.iterdir())
    assert all_files == [pre_existing_file]


def test_scan_creation_cleanup_failure_does_not_mask_original_error(isolated_storage_and_db, monkeypatch):
    """
    Verifies that if cleaning up the image file also raises an exception (e.g. PermissionError),
    the original database error handling is preserved and HTTP 500 is still returned to the client.
    """
    db, upload_root = isolated_storage_and_db

    # Mock db.commit to fail
    def mock_commit():
        raise RuntimeError("Simulated database failure")

    monkeypatch.setattr(db, "commit", mock_commit)

    # Mock unlink to simulate file system permission error during cleanup
    def mock_unlink(self, *args, **kwargs):
        raise PermissionError("Access denied when attempting to delete file")

    monkeypatch.setattr(Path, "unlink", mock_unlink)

    with pytest.raises(HTTPException) as exc_info:
        create_scan_with_image(
            db=db,
            user_id=1,
            file_bytes=TINY_JPEG_BYTES,
            content_type="image/jpeg",
            original_filename="perm_error.jpg",
            crop="tur",
        )

    # HTTP 500 must still be raised cleanly
    assert exc_info.value.status_code == 500
    assert "Scan record could not be saved" in exc_info.value.detail


def test_scan_creation_validation_guards_reject_before_disk_or_db(isolated_storage_and_db):
    """
    Verifies that upload validation errors (empty file, unsupported type, oversized)
    fail early with HTTP 422 before any file is saved to disk or any record is added.
    """
    db, upload_root = isolated_storage_and_db
    scans_dir = upload_root / "scans"

    # 1. Empty image
    with pytest.raises(HTTPException) as exc_empty:
        create_scan_with_image(
            db=db,
            user_id=1,
            file_bytes=b"",
            content_type="image/jpeg",
            original_filename="empty.jpg",
        )
    assert exc_empty.value.status_code == 422
    assert "empty" in str(exc_empty.value.detail).lower()

    # 2. Unsupported MIME type
    with pytest.raises(HTTPException) as exc_mime:
        create_scan_with_image(
            db=db,
            user_id=1,
            file_bytes=b"GIF89a...",
            content_type="image/gif",
            original_filename="leaf.gif",
        )
    assert exc_mime.value.status_code == 422
    assert "unsupported" in str(exc_mime.value.detail).lower()

    # 3. Oversized image (> 20 MB)
    huge_bytes = b"X" * (20 * 1024 * 1024 + 10)
    with pytest.raises(HTTPException) as exc_size:
        create_scan_with_image(
            db=db,
            user_id=1,
            file_bytes=huge_bytes,
            content_type="image/jpeg",
            original_filename="huge.jpg",
        )
    assert exc_size.value.status_code == 422
    assert "exceeds" in str(exc_size.value.detail).lower()

    # Verify scans directory has 0 files and DB has 0 records
    if scans_dir.exists():
        assert len(list(scans_dir.iterdir())) == 0
    assert db.query(TurScan).count() == 0
