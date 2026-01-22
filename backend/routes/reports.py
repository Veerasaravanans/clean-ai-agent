"""
reports.py - Report Generation API Routes

API endpoints for generating, viewing, and downloading test reports.
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from typing import Optional

from backend.services.report_generator import get_report_generator
from backend.models.reports import (
    GenerateReportRequest,
    GenerateReportResponse,
    ReportListResponse,
    ReportDetailResponse,
    DeleteReportResponse,
    ReportFormat
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


# ═══════════════════════════════════════════════════════════
# Generate Report
# ═══════════════════════════════════════════════════════════

@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(request: GenerateReportRequest):
    """
    Generate a new report.

    Args:
        request: Report generation parameters including format, filters, and options

    Returns:
        Report metadata with download/view URLs
    """
    try:
        generator = get_report_generator()
        metadata = generator.generate_report(request)

        return GenerateReportResponse(
            success=True,
            message=f"{metadata.format.value.upper()} report generated successfully",
            data={
                "report_id": metadata.report_id,
                "filename": metadata.filename,
                "format": metadata.format.value,
                "download_url": f"/api/reports/download/{metadata.report_id}",
                "view_url": f"/api/reports/view/{metadata.report_id}",
                "file_size_bytes": metadata.file_size_bytes,
                "executions_included": metadata.executions_included
            }
        )

    except ImportError as e:
        logger.error(f"Missing dependency for report generation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Report generation requires additional dependencies: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# List Reports
# ═══════════════════════════════════════════════════════════

@router.get("/list", response_model=ReportListResponse)
async def list_reports():
    """
    List all generated reports.

    Returns:
        List of report metadata
    """
    try:
        generator = get_report_generator()
        reports = generator.list_reports()

        return ReportListResponse(
            success=True,
            data={
                "reports": reports,
                "total": len(reports)
            }
        )

    except Exception as e:
        logger.error(f"Error listing reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Get Report Details
# ═══════════════════════════════════════════════════════════

@router.get("/details/{report_id}", response_model=ReportDetailResponse)
async def get_report_details(report_id: str):
    """
    Get detailed information about a specific report.

    Args:
        report_id: Report identifier

    Returns:
        Full report metadata
    """
    try:
        generator = get_report_generator()
        metadata = generator.get_report(report_id)

        if not metadata:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

        return ReportDetailResponse(
            success=True,
            data=metadata,
            message="Report details retrieved"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting report details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Download Report
# ═══════════════════════════════════════════════════════════

@router.get("/download/{report_id}")
async def download_report(report_id: str):
    """
    Download a report file.

    Args:
        report_id: Report identifier

    Returns:
        FileResponse with the report file
    """
    try:
        generator = get_report_generator()
        file_path = generator.get_report_path(report_id)

        if not file_path:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

        metadata = generator.get_report(report_id)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
            if metadata.format == ReportFormat.EXCEL else "application/pdf"

        return FileResponse(
            path=str(file_path),
            filename=metadata.filename,
            media_type=media_type
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# View Report
# ═══════════════════════════════════════════════════════════

@router.get("/view/{report_id}", response_class=HTMLResponse)
async def view_report(report_id: str):
    """
    View a report in the browser.

    For PDF: Returns an HTML page with embedded PDF viewer
    For Excel: Returns an HTML page with table preview

    Args:
        report_id: Report identifier

    Returns:
        HTML response for viewing the report
    """
    try:
        generator = get_report_generator()
        metadata = generator.get_report(report_id)

        if not metadata:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

        if metadata.format == ReportFormat.PDF:
            # Return HTML with embedded PDF viewer
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{metadata.title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #fff; }}
        .header {{ padding: 20px; background: #16213e; border-bottom: 2px solid #00d4ff; display: flex; justify-content: space-between; align-items: center; }}
        .header h1 {{ font-size: 20px; color: #00d4ff; }}
        .header .meta {{ font-size: 12px; color: #888; }}
        .actions {{ display: flex; gap: 10px; }}
        .btn {{ padding: 8px 16px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; text-decoration: none; }}
        .btn-primary {{ background: #00d4ff; color: #000; }}
        .btn-secondary {{ background: #3a3a4e; color: #fff; }}
        .btn:hover {{ opacity: 0.9; }}
        .viewer {{ width: 100%; height: calc(100vh - 80px); }}
        iframe {{ width: 100%; height: 100%; border: none; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>{metadata.title}</h1>
            <div class="meta">Generated: {metadata.generated_at[:19]} | Executions: {metadata.executions_included}</div>
        </div>
        <div class="actions">
            <a href="/api/reports/download/{report_id}" class="btn btn-primary">Download PDF</a>
            <a href="javascript:history.back()" class="btn btn-secondary">Close</a>
        </div>
    </div>
    <div class="viewer">
        <iframe src="/api/reports/download/{report_id}" type="application/pdf"></iframe>
    </div>
</body>
</html>
            """
            return HTMLResponse(content=html_content)

        else:
            # Excel preview - generate HTML table from preview data
            preview = generator.get_preview(report_id)
            
            # Build table headers
            headers = preview.executions_table.headers if preview else ["Test ID", "Status", "Duration", "Pass Rate"]
            header_row = "".join(f"<th>{h}</th>" for h in headers)
            
            # Build table rows
            table_rows = ""
            if preview and hasattr(preview, 'executions_table') and hasattr(preview.executions_table, 'rows'):
                for row in preview.executions_table.rows:
                    cells = ""
                    for i, cell in enumerate(row.cells if hasattr(row, 'cells') else []):
                        # Add status class for status column (typically index 1)
                        status_class = f" class=\"status-{str(cell).lower()}\"" if i == 1 else ""
                        cells += f"<td{status_class}>{cell}</td>"
                    table_rows += f"<tr>{cells}</tr>"

            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{metadata.title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #fff; padding: 20px; }}
        .header {{ margin-bottom: 20px; padding-bottom: 20px; border-bottom: 2px solid #00d4ff; display: flex; justify-content: space-between; align-items: center; }}
        .header h1 {{ font-size: 24px; color: #00d4ff; }}
        .header .meta {{ font-size: 12px; color: #888; }}
        .actions {{ display: flex; gap: 10px; }}
        .btn {{ padding: 8px 16px; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; text-decoration: none; }}
        .btn-primary {{ background: #00d4ff; color: #000; }}
        .btn-secondary {{ background: #3a3a4e; color: #fff; }}
        .btn:hover {{ opacity: 0.9; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .summary-card {{ background: #16213e; padding: 15px; border-radius: 8px; border-left: 3px solid #00d4ff; }}
        .summary-card h3 {{ font-size: 12px; color: #888; margin-bottom: 5px; }}
        .summary-card .value {{ font-size: 24px; color: #00d4ff; }}
        table {{ width: 100%; border-collapse: collapse; background: #16213e; border-radius: 8px; overflow: hidden; }}
        th {{ background: #0f3460; color: #00d4ff; padding: 12px; text-align: left; font-weight: 600; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #3a3a4e; }}
        tr:hover {{ background: #1f2a44; }}
        .status-success {{ color: #00ff88; }}
        .status-failure, .status-error {{ color: #ff4444; }}
        .note {{ margin-top: 20px; padding: 15px; background: #16213e; border-radius: 8px; font-size: 12px; color: #888; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>{metadata.title}</h1>
            <div class="meta">Generated: {metadata.generated_at[:19]} | Format: Excel | Executions: {metadata.executions_included}</div>
        </div>
        <div class="actions">
            <a href="/api/reports/download/{report_id}" class="btn btn-primary">Download Excel</a>
            <a href="javascript:history.back()" class="btn btn-secondary">Close</a>
        </div>
    </div>

    <div class="summary">
        <div class="summary-card">
            <h3>Total Executions</h3>
            <div class="value">{metadata.executions_included}</div>
        </div>
        <div class="summary-card">
            <h3>Date Range</h3>
            <div class="value" style="font-size: 14px;">{metadata.date_range or 'N/A'}</div>
        </div>
        <div class="summary-card">
            <h3>File Size</h3>
            <div class="value" style="font-size: 14px;">{metadata.file_size_bytes // 1024} KB</div>
        </div>
    </div>

    <h2 style="color: #00d4ff; margin-bottom: 15px;">Execution Preview</h2>
    <table>
        <thead>
            <tr>
                {header_row}
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>

    <div class="note">
        This is a preview of the Excel report. Download the file to see complete data with charts and multiple sheets.
    </div>
</body>
</html>
            """
            return HTMLResponse(content=html_content)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error viewing report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Delete Report
# ═══════════════════════════════════════════════════════════

@router.delete("/{report_id}", response_model=DeleteReportResponse)
async def delete_report(report_id: str):
    """
    Delete a report file.

    Args:
        report_id: Report identifier

    Returns:
        Success confirmation
    """
    try:
        generator = get_report_generator()

        # Verify exists
        metadata = generator.get_report(report_id)
        if not metadata:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

        # Delete
        success = generator.delete_report(report_id)

        if success:
            return DeleteReportResponse(
                success=True,
                message=f"Report {report_id} deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete report")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════
# Quick Generate Endpoints
# ═══════════════════════════════════════════════════════════

@router.post("/quick/excel")
async def quick_generate_excel(
    include_screenshots: bool = Query(default=False),
    include_ssim: bool = Query(default=True),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None)
):
    """
    Quick endpoint to generate an Excel report with default settings.
    """
    request = GenerateReportRequest(
        format=ReportFormat.EXCEL,
        include_screenshots=include_screenshots,
        include_ssim_details=include_ssim,
        date_from=date_from,
        date_to=date_to
    )
    return await generate_report(request)


@router.post("/quick/pdf")
async def quick_generate_pdf(
    include_charts: bool = Query(default=True),
    include_ssim: bool = Query(default=True),
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None)
):
    """
    Quick endpoint to generate a PDF report with default settings.
    """
    request = GenerateReportRequest(
        format=ReportFormat.PDF,
        include_charts=include_charts,
        include_ssim_details=include_ssim,
        date_from=date_from,
        date_to=date_to
    )
    return await generate_report(request)
