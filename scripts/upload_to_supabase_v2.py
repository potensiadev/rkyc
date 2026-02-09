"""
Supabase Storage에 문서 업로드 스크립트 v2
- 한글 파일명 → corp_id 기반 영문 파일명으로 변환
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

# Supabase 설정
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_PATH = Path(__file__).parent.parent / "data" / "documents" / "upload"
BUCKET_NAME = "documents"

# 기업명 → corp_id 매핑
COMPANY_MAP = {
    "삼성전자": "4301-3456789",
    "엠케이전자": "8001-3719240",
    "동부건설": "8000-7647330",
    "휴림로봇": "6701-4567890",
}

# 문서 타입
DOC_TYPES = ["BIZ_REG", "REGISTRY", "SHAREHOLDERS", "FIN_STATEMENT", "AOI"]


def get_corp_id_from_filename(filename: str) -> str:
    """파일명에서 기업명 추출 후 corp_id 반환"""
    for company_name, corp_id in COMPANY_MAP.items():
        if company_name in filename:
            return corp_id
    return None


def get_doc_type_suffix(doc_type: str) -> str:
    """문서 타입 접미사"""
    suffixes = {
        "BIZ_REG": "biz_reg",
        "REGISTRY": "registry",
        "SHAREHOLDERS": "shareholders",
        "FIN_STATEMENT": "fin_statement",
        "AOI": "aoi",
    }
    return suffixes.get(doc_type, doc_type.lower())


def ensure_bucket_exists():
    """버킷 확인/생성"""
    try:
        buckets = supabase.storage.list_buckets()
        bucket_names = [b.name for b in buckets]

        if BUCKET_NAME not in bucket_names:
            print(f"Creating bucket: {BUCKET_NAME}")
            supabase.storage.create_bucket(
                BUCKET_NAME,
                options={
                    "public": False,
                    "file_size_limit": 52428800,
                    "allowed_mime_types": ["application/pdf", "image/png", "image/jpeg"],
                }
            )
            print(f"Bucket '{BUCKET_NAME}' created")
        else:
            print(f"Bucket '{BUCKET_NAME}' exists")
    except Exception as e:
        print(f"Bucket check/create warning: {e}")


def upload_file(local_path: Path, storage_path: str) -> bool:
    """파일 업로드"""
    try:
        with open(local_path, "rb") as f:
            file_data = f.read()

        # 기존 파일 삭제
        try:
            supabase.storage.from_(BUCKET_NAME).remove([storage_path])
        except:
            pass

        # 업로드
        supabase.storage.from_(BUCKET_NAME).upload(
            storage_path,
            file_data,
            file_options={"content-type": "application/pdf"}
        )
        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    print("=" * 60)
    print("Supabase Storage Upload (v2 - English filenames)")
    print("=" * 60)
    print(f"URL: {SUPABASE_URL}")
    print(f"Bucket: {BUCKET_NAME}")
    print()

    ensure_bucket_exists()

    uploaded = 0
    failed = 0

    for doc_type in DOC_TYPES:
        doc_folder = BASE_PATH / doc_type
        if not doc_folder.exists():
            continue

        print(f"\n[{doc_type}]")

        for pdf_file in doc_folder.glob("*.pdf"):
            corp_id = get_corp_id_from_filename(pdf_file.name)
            if not corp_id:
                print(f"  Skip: {pdf_file.name} (unknown company)")
                continue

            # 새 파일명: {corp_id}_{doc_type}.pdf
            suffix = get_doc_type_suffix(doc_type)
            new_filename = f"{corp_id}_{suffix}.pdf"
            storage_path = f"{doc_type}/{new_filename}"

            print(f"  {pdf_file.name} -> {new_filename}...", end=" ")

            if upload_file(pdf_file, storage_path):
                print("OK")
                uploaded += 1
            else:
                print("FAILED")
                failed += 1

    print("\n" + "=" * 60)
    print(f"Complete: {uploaded} uploaded, {failed} failed")
    print("=" * 60)

    # 업로드된 파일 목록
    print("\nFiles in Supabase Storage:")
    try:
        for doc_type in DOC_TYPES:
            files = supabase.storage.from_(BUCKET_NAME).list(doc_type)
            for f in files:
                if f.get('name'):
                    print(f"  - {doc_type}/{f['name']}")
    except Exception as e:
        print(f"List error: {e}")


if __name__ == "__main__":
    main()
