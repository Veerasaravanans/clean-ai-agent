"""
reports.py - Pydantic models for Report Generation

Models for generating Excel and PDF reports from test execution data.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ReportFormat(str, Enum):
    """Supported report formats."""
    EXCEL = "excel"
    PDF = "pdf"


class ReportType(str, Enum):
    """Type of report content."""
    SUMMARY = "summary"
    DETAILED = "detailed"
    SSIM_ONLY = "ssim_only"
    CUSTOM = "custom"


# ═══════════════════════════════════════════════════════════
# Report Generation Request
# ═══════════════════════════════════════════════════════════

class GenerateReportRequest(BaseModel):
    """Request to generate a report."""
    format: ReportFormat = Field(default=ReportFormat.EXCEL, description="Report format")
    report_type: ReportType = Field(default=ReportType.DETAILED, description="Report type")

    # Content options
    include_screenshots: bool = Field(default=False, description="Include screenshots in report")
    include_ssim_details: bool = Field(default=True, description="Include SSIM verification details")
    include_charts: bool = Field(default=True, description="Include charts/graphs")
    include_step_details: bool = Field(default=True, description="Include individual step details")

    # Filter options
    date_from: Optional[str] = Field(default=None, description="Start date (YYYY-MM-DD)")
    date_to: Optional[str] = Field(default=None, description="End date (YYYY-MM-DD)")
    test_ids: Optional[List[str]] = Field(default=None, description="Specific test IDs to include")
    execution_ids: Optional[List[str]] = Field(default=None, description="Specific execution IDs to include")
    status_filter: Optional[List[str]] = Field(default=None, description="Filter by status (success, failure, etc.)")

    # Report metadata
    title: Optional[str] = Field(default=None, description="Custom report title")
    description: Optional[str] = Field(default=None, description="Report description/notes")


# ═══════════════════════════════════════════════════════════
# Report Metadata
# ═══════════════════════════════════════════════════════════

class ReportMetadata(BaseModel):
    """Metadata for a generated report."""
    report_id: str = Field(..., description="Unique report identifier")
    filename: str = Field(..., description="Report filename")
    format: ReportFormat
    report_type: ReportType

    # Generation info
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    generated_by: str = Field(default="AI Agent Framework")

    # Content info
    title: str = Field(default="Test Execution Report")
    description: Optional[str] = None

    # Data info
    executions_included: int = Field(default=0)
    date_range: Optional[str] = Field(default=None, description="Date range covered")
    test_ids_included: List[str] = Field(default_factory=list)

    # File info
    file_path: str = Field(default="")
    file_size_bytes: int = Field(default=0)

    # Options used
    include_screenshots: bool = False
    include_ssim_details: bool = True
    include_charts: bool = True


# ═══════════════════════════════════════════════════════════
# API Response Models
# ═══════════════════════════════════════════════════════════

class GenerateReportResponse(BaseModel):
    """Response for report generation."""
    success: bool = True
    message: str = ""
    data: Optional[Dict[str, Any]] = Field(default_factory=lambda: {
        "report_id": "",
        "filename": "",
        "format": "",
        "download_url": "",
        "view_url": ""
    })


class ReportListResponse(BaseModel):
    """Response for listing reports."""
    success: bool = True
    data: Dict[str, Any] = Field(default_factory=lambda: {
        "reports": [],
        "total": 0
    })


class ReportDetailResponse(BaseModel):
    """Response for report details."""
    success: bool = True
    data: Optional[ReportMetadata] = None
    message: str = ""


class DeleteReportResponse(BaseModel):
    """Response for report deletion."""
    success: bool = True
    message: str = ""


# ═══════════════════════════════════════════════════════════
# Excel-specific Models
# ═══════════════════════════════════════════════════════════

class ExcelSheetConfig(BaseModel):
    """Configuration for an Excel sheet."""
    name: str = Field(..., description="Sheet name")
    include: bool = Field(default=True)
    columns: Optional[List[str]] = Field(default=None, description="Columns to include")


class ExcelReportConfig(BaseModel):
    """Configuration for Excel report generation."""
    summary_sheet: ExcelSheetConfig = Field(
        default_factory=lambda: ExcelSheetConfig(name="Summary")
    )
    executions_sheet: ExcelSheetConfig = Field(
        default_factory=lambda: ExcelSheetConfig(name="Executions")
    )
    ssim_sheet: ExcelSheetConfig = Field(
        default_factory=lambda: ExcelSheetConfig(name="SSIM Results")
    )
    steps_sheet: ExcelSheetConfig = Field(
        default_factory=lambda: ExcelSheetConfig(name="Step Details")
    )


# ═══════════════════════════════════════════════════════════
# PDF-specific Models
# ═══════════════════════════════════════════════════════════

class PDFSectionConfig(BaseModel):
    """Configuration for a PDF section."""
    name: str
    include: bool = True
    page_break_after: bool = False


class PDFReportConfig(BaseModel):
    """Configuration for PDF report generation."""
    header_section: PDFSectionConfig = Field(
        default_factory=lambda: PDFSectionConfig(name="Header")
    )
    summary_section: PDFSectionConfig = Field(
        default_factory=lambda: PDFSectionConfig(name="Executive Summary", page_break_after=True)
    )
    executions_section: PDFSectionConfig = Field(
        default_factory=lambda: PDFSectionConfig(name="Execution Details")
    )
    ssim_section: PDFSectionConfig = Field(
        default_factory=lambda: PDFSectionConfig(name="SSIM Verification Results")
    )
    charts_section: PDFSectionConfig = Field(
        default_factory=lambda: PDFSectionConfig(name="Charts & Analytics")
    )


# ═══════════════════════════════════════════════════════════
# Report Preview Models
# ═══════════════════════════════════════════════════════════

class ReportPreviewRow(BaseModel):
    """A row in the report preview."""
    cells: List[str] = Field(default_factory=list)


class ReportPreviewTable(BaseModel):
    """A table for report preview."""
    headers: List[str] = Field(default_factory=list)
    rows: List[ReportPreviewRow] = Field(default_factory=list)


class ReportPreview(BaseModel):
    """Preview data for a report (for Excel HTML preview)."""
    summary: Dict[str, Any] = Field(default_factory=dict)
    executions_table: ReportPreviewTable = Field(default_factory=ReportPreviewTable)
    ssim_table: Optional[ReportPreviewTable] = None
    total_pages: int = Field(default=1)
