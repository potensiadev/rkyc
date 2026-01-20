"""
신규 법인 KYC API 엔드포인트
서류 업로드 기반 신규 고객 분석

Security:
- P0-1: MIME Type 검증
- P0-2: Path Traversal 방지 (UUID 검증)
- P0-3: 파일 크기 제한
"""

import json
import logging
import os
import uuid
from datetime import datetime, UTC
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.models.job import Job, JobType, JobStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# ============================================================
# 설정 상수
# ============================================================

# 업로드 파일 저장 경로 (환경변수에서 가져오거나 기본값 사용)
UPLOAD_DIR = getattr(settings, 'NEW_KYC_UPLOAD_DIR', '/tmp/rkyc_uploads')

# 파일 크기 제한
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50MB total

# 허용 MIME Types
ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/x-pdf',
}

# 허용 확장자
ALLOWED_EXTENSIONS = {'.pdf'}


# ============================================================
# 보안 유틸리티
# ============================================================

def validate_uuid(value: str, field_name: str = "job_id") -> uuid.UUID:
    """
    UUID 형식 검증 (P0-2: Path Traversal 방지)
    """
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format. Must be a valid UUID.",
        )


async def validate_upload_file(
    upload_file: UploadFile,
    doc_type: str,
) -> bytes:
    """
    업로드 파일 검증 (P0-1, P0-3)

    - MIME Type 검증
    - 파일 크기 검증
    - 확장자 검증
    """
    # 확장자 검증
    filename = upload_file.filename or ""
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{doc_type}: 허용되지 않는 파일 형식입니다. PDF만 업로드 가능합니다.",
        )

    # 파일 내용 읽기
    content = await upload_file.read()

    # 파일 크기 검증
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{doc_type}: 파일 크기가 10MB를 초과합니다.",
        )

    # MIME Type 검증 (PDF magic bytes: %PDF)
    if len(content) < 4 or not content[:4].startswith(b'%PDF'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{doc_type}: 유효하지 않은 PDF 파일입니다.",
        )

    # 파일 포인터 리셋
    await upload_file.seek(0)

    return content


def get_safe_job_dir(job_id: uuid.UUID) -> str:
    """
    안전한 Job 디렉토리 경로 생성 (P0-2)

    UUID 객체를 사용하므로 Path Traversal 불가능
    """
    # str(uuid.UUID)는 하이픈 포함 표준 형식 반환
    # UUID 객체로 검증되었으므로 안전함
    return os.path.join(UPLOAD_DIR, str(job_id))


# ============================================================
# Pydantic 스키마
# ============================================================

class NewKycAnalyzeResponse(BaseModel):
    job_id: str
    status: str
    message: str


class NewKycJobProgress(BaseModel):
    step: Optional[str] = None
    percent: int = 0


class NewKycJobError(BaseModel):
    code: Optional[str] = None
    message: Optional[str] = None


class NewKycJobStatusResponse(BaseModel):
    job_id: str
    status: str
    corp_name: Optional[str] = None
    progress: NewKycJobProgress
    error: Optional[NewKycJobError] = None


class NewKycEvidence(BaseModel):
    evidence_type: str
    ref_type: str
    ref_value: str
    snippet: Optional[str] = None


class NewKycSignal(BaseModel):
    signal_id: Optional[str] = None
    signal_type: str
    event_type: str
    impact_direction: str
    impact_strength: str
    confidence: str
    title: str
    summary: str
    evidences: List[NewKycEvidence] = []


class NewKycCorpInfo(BaseModel):
    corp_name: Optional[str] = None
    biz_no: Optional[str] = None
    corp_reg_no: Optional[str] = None
    ceo_name: Optional[str] = None
    founded_date: Optional[str] = None
    industry: Optional[str] = None
    capital: Optional[int] = None
    address: Optional[str] = None


class NewKycFinancialSummary(BaseModel):
    year: int
    revenue: Optional[int] = None
    operating_profit: Optional[int] = None
    debt_ratio: Optional[float] = None


class NewKycShareholder(BaseModel):
    name: str
    ownership_pct: float


class NewKycReportResponse(BaseModel):
    job_id: str
    corp_info: NewKycCorpInfo
    financial_summary: Optional[NewKycFinancialSummary] = None
    shareholders: List[NewKycShareholder] = []
    signals: List[NewKycSignal] = []
    insight: Optional[str] = None
    created_at: str


# ============================================================
# API 엔드포인트
# ============================================================

@router.post(
    "/analyze",
    response_model=NewKycAnalyzeResponse,
    summary="신규 법인 KYC 분석 시작",
    description="""
    서류 업로드 기반 신규 법인 KYC 분석을 시작합니다.

    - 최소 사업자등록증 1개 필수
    - 정관, 주주명부, 재무제표, 등기부등본은 선택
    - 서류가 많을수록 분석 정확도 향상
    - 파일당 최대 10MB, 총 50MB 제한
    """,
)
async def analyze_new_kyc(
    corp_name: Optional[str] = Form(None, max_length=200),
    memo: Optional[str] = Form(None, max_length=1000),
    file_BIZ_REG: Optional[UploadFile] = File(None),
    file_AOI: Optional[UploadFile] = File(None),
    file_SHAREHOLDERS: Optional[UploadFile] = File(None),
    file_FINANCIAL: Optional[UploadFile] = File(None),
    file_REGISTRY: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """신규 법인 KYC 분석 시작"""

    # 필수 서류 체크
    if not file_BIZ_REG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="사업자등록증(file_BIZ_REG)은 필수입니다.",
        )

    # 파일 매핑
    file_mapping = {
        "BIZ_REG": file_BIZ_REG,
        "AOI": file_AOI,
        "SHAREHOLDERS": file_SHAREHOLDERS,
        "FINANCIAL": file_FINANCIAL,
        "REGISTRY": file_REGISTRY,
    }

    # 파일 검증 및 내용 읽기
    validated_files: dict[str, bytes] = {}
    total_size = 0

    for doc_type, upload_file in file_mapping.items():
        if upload_file:
            content = await validate_upload_file(upload_file, doc_type)
            validated_files[doc_type] = content
            total_size += len(content)

    # 총 파일 크기 검증
    if total_size > MAX_TOTAL_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"총 파일 크기가 50MB를 초과합니다. (현재: {total_size / 1024 / 1024:.1f}MB)",
        )

    # Job ID 생성 (UUID)
    job_uuid = uuid.uuid4()
    job_id = str(job_uuid)

    # 안전한 Job 디렉토리 생성
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    job_dir = get_safe_job_dir(job_uuid)
    os.makedirs(job_dir, exist_ok=True)

    # 검증된 파일 저장
    saved_files = {}
    for doc_type, content in validated_files.items():
        file_path = os.path.join(job_dir, f"{doc_type}.pdf")
        with open(file_path, "wb") as f:
            f.write(content)
        saved_files[doc_type] = file_path
        logger.info(f"Saved file: {doc_type} -> {file_path} ({len(content)} bytes)")

    # 메타데이터 저장
    meta_path = os.path.join(job_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "corp_name": corp_name,
            "memo": memo,
            "files": list(saved_files.keys()),
            "created_at": datetime.now(UTC).isoformat(),
        }, f, ensure_ascii=False, indent=2)

    # Job 생성
    new_job = Job(
        job_id=job_uuid,
        job_type=JobType.ANALYZE,
        corp_id=None,  # 신규 고객이므로 corp_id 없음
        status=JobStatus.QUEUED,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    # Celery 태스크 실행
    try:
        from app.worker.tasks.new_kyc_analysis import run_new_kyc_pipeline
        task = run_new_kyc_pipeline.delay(job_id, job_dir, corp_name)
        logger.info(f"New KYC analysis task dispatched: job_id={job_id}")
    except Exception as e:
        logger.error(f"Celery dispatch failed: {e}")
        new_job.status = JobStatus.FAILED
        new_job.error_code = "CELERY_DISPATCH_FAILED"
        new_job.error_message = "Worker 연결에 실패했습니다. 잠시 후 다시 시도해주세요."
        await db.commit()

        return NewKycAnalyzeResponse(
            job_id=job_id,
            status="FAILED",
            message="Worker 연결에 실패했습니다. 잠시 후 다시 시도해주세요.",
        )

    return NewKycAnalyzeResponse(
        job_id=job_id,
        status="QUEUED",
        message="신규 법인 KYC 분석이 시작되었습니다.",
    )


@router.get(
    "/jobs/{job_id}",
    response_model=NewKycJobStatusResponse,
    summary="분석 작업 상태 조회",
)
async def get_new_kyc_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """신규 KYC 분석 작업 상태 조회"""

    # UUID 검증 (P0-2)
    job_uuid = validate_uuid(job_id)

    query = text("""
        SELECT job_id, status, progress_step, progress_percent,
               error_code, error_message
        FROM rkyc_job
        WHERE job_id = :job_id
    """)

    result = await db.execute(query, {"job_id": str(job_uuid)})
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="작업을 찾을 수 없습니다.",
        )

    # 안전한 경로로 메타데이터 조회
    corp_name = None
    job_dir = get_safe_job_dir(job_uuid)
    meta_path = os.path.join(job_dir, "meta.json")

    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                corp_name = meta.get("corp_name")
        except (json.JSONDecodeError, IOError):
            pass

    # 결과에서 기업명 조회 (분석 완료 시)
    if not corp_name:
        result_path = os.path.join(job_dir, "result.json")
        if os.path.exists(result_path):
            try:
                with open(result_path, "r", encoding="utf-8") as f:
                    result_data = json.load(f)
                    corp_name = result_data.get("corp_info", {}).get("corp_name")
            except (json.JSONDecodeError, IOError):
                pass

    return NewKycJobStatusResponse(
        job_id=job_id,
        status=row.status,
        corp_name=corp_name,
        progress=NewKycJobProgress(
            step=row.progress_step,
            percent=row.progress_percent or 0,
        ),
        error=NewKycJobError(
            code=row.error_code,
            message=row.error_message,
        ) if row.error_code else None,
    )


@router.get(
    "/report/{job_id}",
    response_model=NewKycReportResponse,
    summary="분석 리포트 조회",
)
async def get_new_kyc_report(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """신규 KYC 분석 리포트 조회"""

    # UUID 검증 (P0-2)
    job_uuid = validate_uuid(job_id)

    # Job 상태 확인
    query = text("SELECT status FROM rkyc_job WHERE job_id = :job_id")
    result = await db.execute(query, {"job_id": str(job_uuid)})
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="작업을 찾을 수 없습니다.",
        )

    if row.status != "DONE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"분석이 아직 완료되지 않았습니다. (현재 상태: {row.status})",
        )

    # 안전한 경로로 결과 파일 읽기
    job_dir = get_safe_job_dir(job_uuid)
    result_path = os.path.join(job_dir, "result.json")

    if not os.path.exists(result_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="분석 결과 파일을 찾을 수 없습니다.",
        )

    try:
        with open(result_path, "r", encoding="utf-8") as f:
            result_data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to read result file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="분석 결과 파일을 읽는 중 오류가 발생했습니다.",
        )

    # 응답 생성
    corp_info = NewKycCorpInfo(**result_data.get("corp_info", {}))

    financial_summary = None
    if result_data.get("financial_summary"):
        financial_summary = NewKycFinancialSummary(**result_data["financial_summary"])

    shareholders = []
    for sh in result_data.get("shareholders", []):
        try:
            shareholders.append(NewKycShareholder(**sh))
        except Exception:
            # 잘못된 형식의 주주 데이터 스킵
            pass

    signals = []
    for sig in result_data.get("signals", []):
        try:
            evidences = [
                NewKycEvidence(**ev)
                for ev in sig.get("evidences", [])
                if isinstance(ev, dict)
            ]
            signals.append(NewKycSignal(
                signal_id=sig.get("signal_id"),
                signal_type=sig.get("signal_type", "DIRECT"),
                event_type=sig.get("event_type", ""),
                impact_direction=sig.get("impact_direction", "NEUTRAL"),
                impact_strength=sig.get("impact_strength", "MED"),
                confidence=sig.get("confidence", "MED"),
                title=sig.get("title", ""),
                summary=sig.get("summary", ""),
                evidences=evidences,
            ))
        except Exception:
            # 잘못된 형식의 시그널 데이터 스킵
            pass

    return NewKycReportResponse(
        job_id=job_id,
        corp_info=corp_info,
        financial_summary=financial_summary,
        shareholders=shareholders,
        signals=signals,
        insight=result_data.get("insight"),
        created_at=result_data.get("created_at", datetime.now(UTC).isoformat()),
    )
