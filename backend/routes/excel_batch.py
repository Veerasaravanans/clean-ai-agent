"""
excel_batch.py - Excel Batch Test Routes

Endpoints for listing Excel files and extracting test IDs for batch execution.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.config import settings
from backend.tools.excel_parser import ExcelParser

logger = logging.getLogger(__name__)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════

class ExcelFileInfo(BaseModel):
    """Information about an Excel file."""
    file_name: str
    file_size: int
    modified_date: str
    test_count: int = 0


class ExcelFilesResponse(BaseModel):
    """Response for listing Excel files."""
    success: bool
    message: str
    files: List[ExcelFileInfo]


class ExtractIdsRequest(BaseModel):
    """Request to extract test IDs from Excel files."""
    file_names: List[str]


class ExtractedTestIds(BaseModel):
    """Test IDs extracted from a single file."""
    file_name: str
    test_ids: List[str]
    test_count: int


class ExtractIdsResponse(BaseModel):
    """Response for extracting test IDs."""
    success: bool
    message: str
    files: List[ExtractedTestIds]
    total_test_ids: int
    all_test_ids: List[str]


# ═══════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/excel/files", response_model=ExcelFilesResponse)
async def list_excel_files():
    """
    List all Excel files in the data/test_cases/ directory.

    Returns:
        List of Excel files with metadata (name, size, modified date)
    """
    logger.info("Listing Excel files in data/test_cases/")

    try:
        # Get the test cases directory from settings
        test_cases_dir = Path(settings.test_cases_dir)

        if not test_cases_dir.exists():
            logger.warning(f"Test cases directory not found: {test_cases_dir}")
            return ExcelFilesResponse(
                success=True,
                message="Test cases directory not found",
                files=[]
            )

        # Find all .xlsx files
        excel_files = []
        for file_path in test_cases_dir.glob("*.xlsx"):
            # Skip temp files (start with ~$)
            if file_path.name.startswith("~$"):
                continue

            try:
                stat = file_path.stat()
                modified_date = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                excel_files.append(ExcelFileInfo(
                    file_name=file_path.name,
                    file_size=stat.st_size,
                    modified_date=modified_date,
                    test_count=0  # Will be populated on extraction
                ))
            except Exception as e:
                logger.warning(f"Error reading file info for {file_path}: {e}")

        # Sort by name
        excel_files.sort(key=lambda x: x.file_name.lower())

        logger.info(f"Found {len(excel_files)} Excel files")

        return ExcelFilesResponse(
            success=True,
            message=f"Found {len(excel_files)} Excel files",
            files=excel_files
        )

    except Exception as e:
        logger.error(f"Error listing Excel files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/excel/extract-ids", response_model=ExtractIdsResponse)
async def extract_test_ids(request: ExtractIdsRequest):
    """
    Extract test IDs from selected Excel files.

    Args:
        request: List of file names to extract IDs from

    Returns:
        Extracted test IDs grouped by file, plus combined list
    """
    logger.info(f"Extracting test IDs from {len(request.file_names)} files")

    try:
        if not request.file_names:
            raise HTTPException(status_code=400, detail="No file names provided")

        test_cases_dir = Path(settings.test_cases_dir)
        parser = ExcelParser()

        extracted_files = []
        all_test_ids = []

        for file_name in request.file_names:
            file_path = test_cases_dir / file_name

            if not file_path.exists():
                logger.warning(f"File not found: {file_name}")
                extracted_files.append(ExtractedTestIds(
                    file_name=file_name,
                    test_ids=[],
                    test_count=0
                ))
                continue

            # Parse the Excel file to get test cases
            test_cases = parser.parse_test_cases(str(file_path))

            # Extract test IDs
            test_ids = [tc["test_id"] for tc in test_cases if tc.get("test_id")]

            # Remove duplicates while preserving order
            seen = set()
            unique_ids = []
            for tid in test_ids:
                if tid not in seen:
                    seen.add(tid)
                    unique_ids.append(tid)

            extracted_files.append(ExtractedTestIds(
                file_name=file_name,
                test_ids=unique_ids,
                test_count=len(unique_ids)
            ))

            all_test_ids.extend(unique_ids)

            logger.info(f"   {file_name}: {len(unique_ids)} test IDs")

        # Remove duplicates from combined list (in case same ID in multiple files)
        seen = set()
        unique_all_ids = []
        for tid in all_test_ids:
            if tid not in seen:
                seen.add(tid)
                unique_all_ids.append(tid)

        logger.info(f"Total unique test IDs: {len(unique_all_ids)}")

        return ExtractIdsResponse(
            success=True,
            message=f"Extracted {len(unique_all_ids)} unique test IDs from {len(request.file_names)} files",
            files=extracted_files,
            total_test_ids=len(unique_all_ids),
            all_test_ids=unique_all_ids
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting test IDs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
