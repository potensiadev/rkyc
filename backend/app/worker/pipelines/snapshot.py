"""
Snapshot Pipeline Stage
Stage 1: Collect internal snapshot data for analysis
"""

import logging
from typing import Optional

from sqlalchemy import select

from app.worker.db import get_sync_db
from app.models.snapshot import InternalSnapshot, InternalSnapshotLatest
from app.models.corporation import Corporation

logger = logging.getLogger(__name__)


class NoSnapshotError(Exception):
    """Raised when no snapshot exists for the corporation"""
    pass


class NoCorporationError(Exception):
    """Raised when corporation is not found"""
    pass


class SnapshotPipeline:
    """
    Stage 1: SNAPSHOT - Collect internal snapshot data

    Retrieves the latest internal snapshot for a corporation.
    The snapshot contains financial, credit, collateral, and KYC data.
    """

    def execute(self, corp_id: str) -> dict:
        """
        Execute snapshot collection stage.

        Args:
            corp_id: Corporation ID

        Returns:
            dict containing:
                - corp_id: Corporation ID
                - snapshot_id: Snapshot UUID
                - snapshot_version: Snapshot version number
                - snapshot_json: Full snapshot data (PRD 7장 스키마)
                - corporation: Corporation info dict

        Raises:
            NoCorporationError: If corporation not found
            NoSnapshotError: If no snapshot exists
        """
        logger.info(f"SNAPSHOT stage starting for corp_id={corp_id}")

        with get_sync_db() as db:
            # 1. Fetch corporation info
            corp_query = select(Corporation).where(Corporation.corp_id == corp_id)
            corp_result = db.execute(corp_query)
            corporation = corp_result.scalar_one_or_none()

            if not corporation:
                raise NoCorporationError(f"Corporation not found: {corp_id}")

            # 2. Get latest snapshot pointer
            latest_query = select(InternalSnapshotLatest).where(
                InternalSnapshotLatest.corp_id == corp_id
            )
            latest_result = db.execute(latest_query)
            latest = latest_result.scalar_one_or_none()

            if not latest:
                raise NoSnapshotError(f"No snapshot found for corp_id={corp_id}")

            # 3. Fetch actual snapshot data
            snapshot_query = select(InternalSnapshot).where(
                InternalSnapshot.snapshot_id == latest.snapshot_id
            )
            snapshot_result = db.execute(snapshot_query)
            snapshot = snapshot_result.scalar_one_or_none()

            if not snapshot:
                raise NoSnapshotError(f"Snapshot data not found: {latest.snapshot_id}")

            logger.info(
                f"SNAPSHOT stage completed: version={snapshot.snapshot_version}, "
                f"corp_name={corporation.corp_name}"
            )

            return {
                "corp_id": corp_id,
                "snapshot_id": str(snapshot.snapshot_id),
                "snapshot_version": snapshot.snapshot_version,
                "snapshot_json": snapshot.snapshot_json,
                "corporation": {
                    "corp_id": corporation.corp_id,
                    "corp_name": corporation.corp_name,
                    "corp_reg_no": corporation.corp_reg_no,
                    "biz_no": corporation.biz_no,
                    "industry_code": corporation.industry_code,
                    "ceo_name": corporation.ceo_name,
                    # DART 공시 기반 정보 (100% Fact 데이터)
                    "dart_corp_code": getattr(corporation, 'dart_corp_code', None),
                    "established_date": getattr(corporation, 'established_date', None),
                    "headquarters": getattr(corporation, 'headquarters', None),
                    "corp_class": getattr(corporation, 'corp_class', None),
                    "homepage_url": getattr(corporation, 'homepage_url', None),
                    "jurir_no": getattr(corporation, 'jurir_no', None),
                    "corp_name_eng": getattr(corporation, 'corp_name_eng', None),
                    "acc_mt": getattr(corporation, 'acc_mt', None),
                    "dart_updated_at": str(corporation.dart_updated_at) if getattr(corporation, 'dart_updated_at', None) else None,
                },
            }
