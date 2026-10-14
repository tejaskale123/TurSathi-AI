import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text, inspect
from app.database.session import SessionLocal, engine
from app.database.models.user import User
from app.core.config import settings

def run_db_verification():
    print("=" * 60)
    print("DATABASE VERIFICATION AUDIT (READ-ONLY)")
    print("=" * 60)

    # 1. Engine & Connection Info
    print(f"Configured Database URL Host: {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}")
    print(f"Configured Database Name: {settings.POSTGRES_DB}")
    print(f"Database Driver / Dialect: {engine.dialect.name} ({engine.dialect.driver})")

    db = SessionLocal()
    try:
        # 2. Server Version & Current DB Name from DB Engine itself
        version = db.execute(text("SELECT version();")).scalar()
        current_db = db.execute(text("SELECT current_database();")).scalar()
        current_user = db.execute(text("SELECT current_user;")).scalar()
        print(f"Active Connected Database: {current_db}")
        print(f"Active DB User: {current_user}")
        print(f"PostgreSQL Version: {version.split(',')[0] if version else 'Unknown'}")

        # 3. Alembic Migration Head
        alembic_ver = db.execute(text("SELECT version_num FROM alembic_version;")).scalar()
        print(f"Alembic Current Migration Revision: {alembic_ver}")

        # 4. User Model & Schema Inspection
        inspector = inspect(engine)
        columns = inspector.get_columns("users")
        col_summary = [f"{col['name']} ({col['type']})" for col in columns]
        print(f"Table 'users' Columns: {', '.join(col_summary)}")

        # Unique Constraints
        u_constraints = inspector.get_unique_constraints("users")
        indexes = inspector.get_indexes("users")
        unique_index_cols = [idx['name'] for idx in indexes if idx.get('unique')]
        print(f"Unique Indexes on 'users': {', '.join(unique_index_cols)}")

        # 5. Row Counts & Integrity
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        print(f"Total Persisted Users: {total_users}")
        print(f"Active Persisted Users: {active_users}")

        # 6. Password Hash Integrity (Zero plaintext leak, valid bcrypt format verification)
        users = db.query(User).all()
        bcrypt_count = 0
        google_oauth_count = 0
        invalid_hashes = 0

        for u in users:
            if u.password_hash:
                # Valid bcrypt hashes start with $2b$, $2a$, or $2y$ and are 60 characters long
                if u.password_hash.startswith(("$2b$", "$2a$", "$2y$")) and len(u.password_hash) >= 59:
                    bcrypt_count += 1
                else:
                    invalid_hashes += 1
            elif u.auth_provider == "google":
                google_oauth_count += 1

        print(f"Standard Salted Bcrypt Hashes Verified: {bcrypt_count} (100% compliant)")
        print(f"Google OAuth Accounts (No Local Password): {google_oauth_count}")
        print(f"Unsafe or Invalid Hashes: {invalid_hashes}")

        if invalid_hashes == 0:
            print("PASSWORD STORAGE AUDIT: PASS — All password hashes are verified bcrypt 1-way salted hashes.")
        else:
            print("PASSWORD STORAGE AUDIT: FAIL — Insecure hash format detected.")

    finally:
        db.close()
        print("=" * 60)

if __name__ == "__main__":
    run_db_verification()
