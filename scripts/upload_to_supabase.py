"""
Supabase Storage에 문서 업로드 스크립트
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# .env 파일 로드
env_path = Path(__file__).parent.parent / "backend" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print(f"Warning: .env file not found at {env_path}")
    print("Please create backend/.env with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")

# Supabase 설정
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Service Role Key 필요 (파일 업로드용)

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    print("\nPlease set in backend/.env:")
    print("  SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co")
    print("  SUPABASE_SERVICE_ROLE_KEY=your_service_role_key")
    sys.exit(1)

# Supabase 클라이언트 생성
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 문서 경로
BASE_PATH = Path(__file__).parent.parent / "data" / "documents" / "upload"
BUCKET_NAME = "documents"

# 문서 타입별 폴더
DOC_TYPES = {
    "BIZ_REG": "사업자등록증",
    "REGISTRY": "등기부등본",
    "SHAREHOLDERS": "주주명부",
    "FIN_STATEMENT": "재무제표",
    "AOI": "정관",
}


def ensure_bucket_exists():
    """버킷이 없으면 생성"""
    try:
        # 버킷 목록 확인
        buckets = supabase.storage.list_buckets()
        bucket_names = [b.name for b in buckets]

        if BUCKET_NAME not in bucket_names:
            print(f"Creating bucket: {BUCKET_NAME}")
            supabase.storage.create_bucket(
                BUCKET_NAME,
                options={
                    "public": False,  # 비공개 버킷
                    "file_size_limit": 52428800,  # 50MB
                    "allowed_mime_types": ["application/pdf", "image/png", "image/jpeg"],
                }
            )
            print(f"Bucket '{BUCKET_NAME}' created successfully")
        else:
            print(f"Bucket '{BUCKET_NAME}' already exists")
    except Exception as e:
        print(f"Warning: Could not check/create bucket: {e}")
        print("Proceeding with upload...")


def upload_file(local_path: Path, storage_path: str) -> bool:
    """파일 업로드"""
    try:
        with open(local_path, "rb") as f:
            file_data = f.read()

        # 기존 파일 삭제 (있으면)
        try:
            supabase.storage.from_(BUCKET_NAME).remove([storage_path])
        except:
            pass  # 파일이 없으면 무시

        # 업로드
        response = supabase.storage.from_(BUCKET_NAME).upload(
            storage_path,
            file_data,
            file_options={"content-type": "application/pdf"}
        )

        return True
    except Exception as e:
        print(f"  Error uploading {storage_path}: {e}")
        return False


def main():
    print("=" * 60)
    print("Supabase Storage 문서 업로드")
    print("=" * 60)
    print(f"\nSupabase URL: {SUPABASE_URL}")
    print(f"Bucket: {BUCKET_NAME}")
    print(f"Local Path: {BASE_PATH}\n")

    # 버킷 확인/생성
    ensure_bucket_exists()

    uploaded = 0
    failed = 0

    # 각 문서 타입별로 업로드
    for doc_type, doc_name in DOC_TYPES.items():
        doc_folder = BASE_PATH / doc_type

        if not doc_folder.exists():
            print(f"\n[{doc_type}] Folder not found: {doc_folder}")
            continue

        print(f"\n[{doc_type}] {doc_name}")

        # PDF 파일들 업로드
        for pdf_file in doc_folder.glob("*.pdf"):
            storage_path = f"{doc_type}/{pdf_file.name}"

            print(f"  Uploading: {pdf_file.name}...", end=" ")

            if upload_file(pdf_file, storage_path):
                print("OK")
                uploaded += 1
            else:
                print("FAILED")
                failed += 1

    print("\n" + "=" * 60)
    print(f"Upload Complete: {uploaded} files uploaded, {failed} failed")
    print("=" * 60)

    # 업로드된 파일 목록 출력
    print("\nUploaded files in Supabase Storage:")
    try:
        for doc_type in DOC_TYPES.keys():
            files = supabase.storage.from_(BUCKET_NAME).list(doc_type)
            for f in files:
                print(f"  - {doc_type}/{f['name']}")
    except Exception as e:
        print(f"Could not list files: {e}")


if __name__ == "__main__":
    main()
