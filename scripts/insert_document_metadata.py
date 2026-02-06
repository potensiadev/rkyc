"""
Supabase DB에 문서 메타데이터 삽입 스크립트
- rkyc_document 테이블에 30개 레코드 삽입
- 로컬 파일: 한글 파일명
- Storage: 영문 파일명 (corp_id 기반)
"""

import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime
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

# 로컬 문서 경로
BASE_PATH = Path(__file__).parent.parent / "data" / "documents" / "upload"

# 기업 매핑
COMPANIES = [
    ("삼성전자", "4301-3456789"),
    ("엠케이전자", "8001-3719240"),
    ("동부건설", "8000-7647330"),
    ("휴림로봇", "6701-4567890"),
    ("전북식품", "4028-1234567"),
    ("광주정밀기계", "6201-2345678"),
]

# 문서 타입별 로컬 파일명 패턴과 Storage 경로
DOC_CONFIG = {
    "BIZ_REG": {
        "local_pattern": "{company_name}_사업자등록증.pdf",
        "storage_suffix": "biz_reg",
    },
    "REGISTRY": {
        "local_patterns": [
            "등기부등본_{company_name}.pdf",
            "사업자정보_{company_name}.pdf",
        ],
        "storage_suffix": "registry",
    },
    "SHAREHOLDERS": {
        "local_pattern": "{company_name}_주주명부.pdf",
        "storage_suffix": "shareholders",
    },
    "FIN_STATEMENT": {
        "local_pattern": "{company_name}_재무제표.pdf",
        "storage_suffix": "fin_statement",
    },
    "AOI": {
        "local_pattern": "{company_name}_정관.pdf",
        "storage_suffix": "aoi",
    },
}


def compute_file_hash(file_path: Path) -> str:
    """파일 SHA256 해시 계산"""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def find_local_file(doc_type: str, company_name: str) -> Path | None:
    """로컬 파일 찾기"""
    config = DOC_CONFIG[doc_type]
    folder = BASE_PATH / doc_type

    if "local_pattern" in config:
        filename = config["local_pattern"].format(company_name=company_name)
        path = folder / filename
        if path.exists():
            return path
    elif "local_patterns" in config:
        for pattern in config["local_patterns"]:
            filename = pattern.format(company_name=company_name)
            path = folder / filename
            if path.exists():
                return path

    return None


def main():
    print("=" * 60)
    print("rkyc_document 메타데이터 삽입")
    print("=" * 60)
    print(f"Supabase URL: {SUPABASE_URL}")
    print()

    inserted = 0
    skipped = 0
    failed = 0

    for company_name, corp_id in COMPANIES:
        print(f"\n[{company_name}] corp_id={corp_id}")

        for doc_type, config in DOC_CONFIG.items():
            # 로컬 파일 찾기
            local_path = find_local_file(doc_type, company_name)

            if not local_path:
                print(f"  - {doc_type}: 로컬 파일 없음")
                failed += 1
                continue

            # Storage 경로 (영문)
            suffix = config["storage_suffix"]
            storage_path = f"{doc_type}/{corp_id}_{suffix}.pdf"

            # 파일 해시 계산
            file_hash = compute_file_hash(local_path)

            # 중복 확인
            existing = supabase.table("rkyc_document").select("doc_id").eq(
                "corp_id", corp_id
            ).eq("doc_type", doc_type).execute()

            if existing.data:
                print(f"  - {doc_type}: 이미 존재, 건너뜀")
                skipped += 1
                continue

            # 삽입
            try:
                result = supabase.table("rkyc_document").insert({
                    "corp_id": corp_id,
                    "doc_type": doc_type,
                    "storage_provider": "SUPABASE",
                    "storage_path": storage_path,
                    "file_hash": file_hash,
                    "page_count": 1,
                    "captured_at": datetime.now().isoformat(),
                    "ingest_status": "PENDING",
                }).execute()

                print(f"  - {doc_type}: OK (hash={file_hash[:8]}...)")
                inserted += 1

            except Exception as e:
                print(f"  - {doc_type}: FAILED - {e}")
                failed += 1

    print("\n" + "=" * 60)
    print(f"완료: {inserted} 삽입, {skipped} 건너뜀, {failed} 실패")
    print("=" * 60)

    # 삽입된 레코드 확인
    print("\n[rkyc_document 전체 목록]")
    try:
        docs = supabase.table("rkyc_document").select(
            "corp_id, doc_type, storage_path, ingest_status"
        ).order("corp_id").order("doc_type").execute()

        for doc in docs.data:
            print(f"  {doc['corp_id']} | {doc['doc_type']:15} | {doc['ingest_status']}")

        print(f"\n총 {len(docs.data)}개 레코드")

    except Exception as e:
        print(f"목록 조회 실패: {e}")


if __name__ == "__main__":
    main()
