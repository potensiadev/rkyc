"""
신규 법인 KYC API 엔드포인트
서류 업로드 기반 신규 고객 분석
"""

import logging
import os
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel

from app.core.database import get_db
from app.models.job import Job, JobType, JobStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# 업로드 파일 저장 경로
UPLOAD_DIR = "/tmp/rkyc_uploads"


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
    """,
)
async def analyze_new_kyc(
    corp_name: Optional[str] = Form(None),
    memo: Optional[str] = Form(None),
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

    # 업로드 디렉토리 생성
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Job ID 생성
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    # 파일 저장
    saved_files = {}
    file_mapping = {
        "BIZ_REG": file_BIZ_REG,
        "AOI": file_AOI,
        "SHAREHOLDERS": file_SHAREHOLDERS,
        "FINANCIAL": file_FINANCIAL,
        "REGISTRY": file_REGISTRY,
    }

    for doc_type, upload_file in file_mapping.items():
        if upload_file:
            file_path = os.path.join(job_dir, f"{doc_type}.pdf")
            content = await upload_file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            saved_files[doc_type] = file_path
            logger.info(f"Saved file: {doc_type} -> {file_path}")

    # 메타데이터 저장
    meta_path = os.path.join(job_dir, "meta.json")
    import json
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "corp_name": corp_name,
            "memo": memo,
            "files": list(saved_files.keys()),
            "created_at": datetime.utcnow().isoformat(),
        }, f, ensure_ascii=False, indent=2)

    # Job 생성
    new_job = Job(
        job_id=uuid.UUID(job_id),
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
        new_job.error_message = str(e)[:200]
        await db.commit()

        return NewKycAnalyzeResponse(
            job_id=job_id,
            status="FAILED",
            message=f"Worker 연결 실패: {str(e)[:100]}",
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

    query = text("""
        SELECT job_id, status, progress_step, progress_percent,
               error_code, error_message
        FROM rkyc_job
        WHERE job_id = :job_id
    """)

    result = await db.execute(query, {"job_id": job_id})
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    # 메타데이터에서 기업명 조회
    corp_name = None
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    meta_path = os.path.join(job_dir, "meta.json")
    if os.path.exists(meta_path):
        import json
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            corp_name = meta.get("corp_name")

    # 결과에서 기업명 조회 (분석 완료 시)
    if not corp_name:
        result_path = os.path.join(job_dir, "result.json")
        if os.path.exists(result_path):
            import json
            with open(result_path, "r", encoding="utf-8") as f:
                result_data = json.load(f)
                corp_name = result_data.get("corp_info", {}).get("corp_name")

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

    # Job 상태 확인
    query = text("SELECT status FROM rkyc_job WHERE job_id = :job_id")
    result = await db.execute(query, {"job_id": job_id})
    row = result.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )

    if row.status != "DONE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analysis not completed. Current status: {row.status}",
        )

    # 결과 파일 읽기
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    result_path = os.path.join(job_dir, "result.json")

    if not os.path.exists(result_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis result not found.",
        )

    import json
    with open(result_path, "r", encoding="utf-8") as f:
        result_data = json.load(f)

    # 응답 생성
    corp_info = NewKycCorpInfo(**result_data.get("corp_info", {}))

    financial_summary = None
    if result_data.get("financial_summary"):
        financial_summary = NewKycFinancialSummary(**result_data["financial_summary"])

    shareholders = [
        NewKycShareholder(**sh)
        for sh in result_data.get("shareholders", [])
    ]

    signals = []
    for sig in result_data.get("signals", []):
        evidences = [
            NewKycEvidence(**ev)
            for ev in sig.get("evidences", [])
        ]
        signals.append(NewKycSignal(
            signal_id=sig.get("signal_id"),
            signal_type=sig.get("signal_type", ""),
            event_type=sig.get("event_type", ""),
            impact_direction=sig.get("impact_direction", "NEUTRAL"),
            impact_strength=sig.get("impact_strength", "MED"),
            confidence=sig.get("confidence", "MED"),
            title=sig.get("title", ""),
            summary=sig.get("summary", ""),
            evidences=evidences,
        ))

    return NewKycReportResponse(
        job_id=job_id,
        corp_info=corp_info,
        financial_summary=financial_summary,
        shareholders=shareholders,
        signals=signals,
        insight=result_data.get("insight"),
        created_at=result_data.get("created_at", datetime.utcnow().isoformat()),
    )
