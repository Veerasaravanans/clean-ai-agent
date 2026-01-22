"""
report_generator.py - Report Generation Service

Generates Excel and PDF reports from test execution history.
"""

import logging
import json
import uuid
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from io import BytesIO

from backend.models.reports import (
    ReportFormat,
    ReportType,
    ReportMetadata,
    GenerateReportRequest,
    ReportPreview,
    ReportPreviewTable,
    ReportPreviewRow
)
from backend.services.test_history_service import get_test_history_service

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Service for generating Excel and PDF reports."""

    def __init__(self, reports_dir: str = "data/reports"):
        """
        Initialize report generator.

        Args:
            reports_dir: Directory for storing generated reports
        """
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_file = self.reports_dir / "reports_index.json"
        self.reports_metadata = self._load_metadata()

        logger.info(f"Report Generator initialized - Dir: {self.reports_dir}")

    def _load_metadata(self) -> Dict:
        """Load reports metadata index."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load reports metadata: {e}")
                return {"reports": []}
        return {"reports": []}

    def _save_metadata(self):
        """Save reports metadata index."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.reports_metadata, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save reports metadata: {e}")

    # ═══════════════════════════════════════════════════════════
    # Main Generation Methods
    # ═══════════════════════════════════════════════════════════

    def generate_report(self, request: GenerateReportRequest) -> ReportMetadata:
        """
        Generate a report based on request parameters.

        Args:
            request: Report generation request

        Returns:
            ReportMetadata with file info
        """
        logger.info(f"Generating {request.format.value} report")

        # Get execution data
        history_service = get_test_history_service()
        executions = self._get_filtered_executions(request, history_service)

        if not executions:
            logger.warning("No executions found for report")

        # Generate report ID
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        # Generate based on format
        if request.format == ReportFormat.EXCEL:
            metadata = self._generate_excel(report_id, request, executions)
        else:
            metadata = self._generate_pdf(report_id, request, executions)

        # Save metadata
        self.reports_metadata["reports"].insert(0, metadata.model_dump())
        self._save_metadata()

        logger.info(f"Report generated: {metadata.filename}")
        return metadata

    def _get_filtered_executions(
        self,
        request: GenerateReportRequest,
        history_service
    ) -> List[Dict[str, Any]]:
        """Get filtered execution data for report."""
        # Get all executions with filters
        result = history_service.list_executions(
            page=1,
            page_size=1000,  # Get all
            test_id=request.test_ids[0] if request.test_ids and len(request.test_ids) == 1 else None,
            date_from=request.date_from,
            date_to=request.date_to,
            sort_by="started_at",
            sort_order="desc"
        )

        executions = result["executions"]

        # Additional filtering
        if request.test_ids and len(request.test_ids) > 1:
            executions = [e for e in executions if e["test_id"] in request.test_ids]

        if request.execution_ids:
            executions = [e for e in executions if e["execution_id"] in request.execution_ids]

        if request.status_filter:
            executions = [e for e in executions if e["status"] in request.status_filter]

        # Get full records for detailed info
        full_executions = []
        for exec_summary in executions:
            full_record = history_service.get_execution(exec_summary["execution_id"])
            if full_record:
                full_executions.append(full_record.model_dump())

        return full_executions

    # ═══════════════════════════════════════════════════════════
    # Excel Generation
    # ═══════════════════════════════════════════════════════════

    def _generate_excel(
        self,
        report_id: str,
        request: GenerateReportRequest,
        executions: List[Dict]
    ) -> ReportMetadata:
        """Generate Excel report."""
        try:
            import xlsxwriter
        except ImportError:
            logger.error("xlsxwriter not installed")
            raise ImportError("xlsxwriter is required for Excel reports")

        filename = f"{report_id}.xlsx"
        file_path = self.reports_dir / filename

        # Create workbook
        workbook = xlsxwriter.Workbook(str(file_path))

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'bg_color': '#1a1a2e',
            'font_color': '#00d4ff',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 18,
            'font_color': '#00d4ff',
            'align': 'center'
        })

        subtitle_format = workbook.add_format({
            'font_size': 12,
            'font_color': '#888888',
            'align': 'center'
        })

        cell_format = workbook.add_format({
            'border': 1,
            'align': 'left',
            'valign': 'vcenter'
        })

        number_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '#,##0'
        })

        percent_format = workbook.add_format({
            'border': 1,
            'align': 'right',
            'valign': 'vcenter',
            'num_format': '0.0%'
        })

        success_format = workbook.add_format({
            'border': 1,
            'bg_color': '#00ff88',
            'font_color': '#000000',
            'align': 'center'
        })

        failure_format = workbook.add_format({
            'border': 1,
            'bg_color': '#ff4444',
            'font_color': '#ffffff',
            'align': 'center'
        })

        # === Summary Sheet ===
        summary_sheet = workbook.add_worksheet("Summary")
        summary_sheet.set_column('A:A', 25)
        summary_sheet.set_column('B:B', 20)

        # Title
        summary_sheet.merge_range('A1:B1', request.title or 'Test Execution Report', title_format)
        summary_sheet.merge_range('A2:B2', f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', subtitle_format)

        # Stats
        total = len(executions)
        passed = sum(1 for e in executions if e["status"] == "success")
        failed = total - passed

        row = 4
        summary_sheet.write(row, 0, "Total Executions", header_format)
        summary_sheet.write(row, 1, total, number_format)
        row += 1
        summary_sheet.write(row, 0, "Passed", header_format)
        summary_sheet.write(row, 1, passed, number_format)
        row += 1
        summary_sheet.write(row, 0, "Failed", header_format)
        summary_sheet.write(row, 1, failed, number_format)
        row += 1
        summary_sheet.write(row, 0, "Pass Rate", header_format)
        summary_sheet.write(row, 1, passed/total if total > 0 else 0, percent_format)

        # Add chart if requested
        if request.include_charts and total > 0:
            chart = workbook.add_chart({'type': 'pie'})
            chart.add_series({
                'name': 'Test Results',
                'categories': ['Summary', 5, 0, 6, 0],
                'values': ['Summary', 5, 1, 6, 1],
                'data_labels': {'percentage': True}
            })
            chart.set_title({'name': 'Pass/Fail Distribution'})
            summary_sheet.insert_chart('D4', chart)

        # === Executions Sheet ===
        exec_sheet = workbook.add_worksheet("Executions")
        exec_headers = ["Execution ID", "Test ID", "Title", "Status", "Started", "Duration (ms)",
                        "Total Steps", "Passed Steps", "Failed Steps", "Pass Rate", "SSIM Rate"]

        for col, header in enumerate(exec_headers):
            exec_sheet.write(0, col, header, header_format)
            exec_sheet.set_column(col, col, 15)

        for row, exec_data in enumerate(executions, start=1):
            exec_sheet.write(row, 0, exec_data["execution_id"], cell_format)
            exec_sheet.write(row, 1, exec_data["test_id"], cell_format)
            exec_sheet.write(row, 2, exec_data.get("test_title", ""), cell_format)

            status = exec_data["status"]
            status_fmt = success_format if status == "success" else failure_format
            exec_sheet.write(row, 3, status.upper(), status_fmt)

            exec_sheet.write(row, 4, exec_data["started_at"][:19], cell_format)
            exec_sheet.write(row, 5, exec_data.get("duration_ms", 0), number_format)
            exec_sheet.write(row, 6, exec_data.get("total_steps", 0), number_format)
            exec_sheet.write(row, 7, exec_data.get("passed_steps", 0), number_format)
            exec_sheet.write(row, 8, exec_data.get("failed_steps", 0), number_format)

            total_steps = exec_data.get("total_steps", 0)
            passed_steps = exec_data.get("passed_steps", 0)
            pass_rate = passed_steps / total_steps if total_steps > 0 else 0
            exec_sheet.write(row, 9, pass_rate, percent_format)

            ssim_total = exec_data.get("ssim_verifications", 0)
            ssim_passed = exec_data.get("ssim_passed", 0)
            ssim_rate = ssim_passed / ssim_total if ssim_total > 0 else 0
            exec_sheet.write(row, 10, ssim_rate, percent_format)

        # === SSIM Results Sheet ===
        if request.include_ssim_details:
            ssim_sheet = workbook.add_worksheet("SSIM Results")
            ssim_headers = ["Execution ID", "Test ID", "Step #", "Description", "SSIM Score", "Passed", "Timestamp"]

            for col, header in enumerate(ssim_headers):
                ssim_sheet.write(0, col, header, header_format)
                ssim_sheet.set_column(col, col, 15)

            ssim_row = 1
            for exec_data in executions:
                for step in exec_data.get("steps", []):
                    if step.get("ssim_score") is not None:
                        ssim_sheet.write(ssim_row, 0, exec_data["execution_id"], cell_format)
                        ssim_sheet.write(ssim_row, 1, exec_data["test_id"], cell_format)
                        ssim_sheet.write(ssim_row, 2, step["step_number"], number_format)
                        ssim_sheet.write(ssim_row, 3, step.get("description", ""), cell_format)
                        ssim_sheet.write(ssim_row, 4, step["ssim_score"], number_format)

                        passed = step.get("ssim_passed", False)
                        fmt = success_format if passed else failure_format
                        ssim_sheet.write(ssim_row, 5, "PASS" if passed else "FAIL", fmt)

                        ssim_sheet.write(ssim_row, 6, step.get("timestamp", ""), cell_format)
                        ssim_row += 1

        # === Step Details Sheet (Enhanced) ===
        if request.include_step_details:
            self._add_step_details_sheet_enhanced(
                workbook, executions, header_format, cell_format,
                number_format, success_format, failure_format
            )

        # === Comparison Images Sheet ===
        if request.include_screenshots:
            comparison_sheet = workbook.add_worksheet("Comparison Images")
            comp_headers = ["Execution ID", "Test ID", "Step #", "Description",
                          "SSIM Score", "Result", "Comparison Image Path"]

            for col, header in enumerate(comp_headers):
                comparison_sheet.write(0, col, header, header_format)
                widths = [15, 15, 6, 30, 10, 8, 50]
                comparison_sheet.set_column(col, col, widths[col] if col < len(widths) else 15)

            comp_row = 1
            for exec_data in executions:
                for step in exec_data.get("steps", []):
                    comp_path = step.get("comparison_image_path")
                    if comp_path:
                        comparison_sheet.write(comp_row, 0, exec_data["execution_id"], cell_format)
                        comparison_sheet.write(comp_row, 1, exec_data["test_id"], cell_format)
                        comparison_sheet.write(comp_row, 2, step.get("step_number", 0), number_format)
                        comparison_sheet.write(comp_row, 3, step.get("description", ""), cell_format)

                        ssim_score = step.get("ssim_score")
                        if ssim_score is not None:
                            comparison_sheet.write(comp_row, 4, f"{ssim_score:.4f}", number_format)

                        ssim_passed = step.get("ssim_passed")
                        if ssim_passed is not None:
                            fmt = success_format if ssim_passed else failure_format
                            comparison_sheet.write(comp_row, 5, "PASS" if ssim_passed else "FAIL", fmt)

                        comparison_sheet.write(comp_row, 6, comp_path, cell_format)
                        comp_row += 1

        workbook.close()

        # Get file size
        file_size = os.path.getsize(file_path)

        # Build date range string
        dates = [e["started_at"][:10] for e in executions if e.get("started_at")]
        date_range = f"{min(dates)} to {max(dates)}" if dates else None

        return ReportMetadata(
            report_id=report_id,
            filename=filename,
            format=ReportFormat.EXCEL,
            report_type=request.report_type,
            title=request.title or "Test Execution Report",
            description=request.description,
            executions_included=len(executions),
            date_range=date_range,
            test_ids_included=list(set(e["test_id"] for e in executions)),
            file_path=str(file_path),
            file_size_bytes=file_size,
            include_screenshots=request.include_screenshots,
            include_ssim_details=request.include_ssim_details,
            include_charts=request.include_charts
        )

    # ═══════════════════════════════════════════════════════════
    # Step Details Sheet (Enhanced)
    # ═══════════════════════════════════════════════════════════

    def _add_step_details_sheet_enhanced(
        self,
        workbook,
        executions: List[Dict],
        header_format,
        cell_format,
        number_format,
        success_format,
        failure_format
    ):
        """Add enhanced step details sheet with all step information."""
        steps_sheet = workbook.add_worksheet("Step Details")

        # Enhanced headers
        step_headers = [
            "Execution ID", "Test ID", "Step #", "Description", "Goal",
            "Action", "Target", "X", "Y", "Coord Source",
            "SSIM Score", "SSIM Passed", "Threshold", "Reference Image",
            "Learned Solution", "Status", "Duration (ms)", "Comparison Image", "Error"
        ]

        for col, header in enumerate(step_headers):
            steps_sheet.write(0, col, header, header_format)
            # Set column widths
            widths = [15, 15, 6, 25, 20, 8, 15, 6, 6, 12, 10, 10, 8, 20, 12, 10, 10, 30, 25]
            steps_sheet.set_column(col, col, widths[col] if col < len(widths) else 15)

        step_row = 1
        for exec_data in executions:
            for step in exec_data.get("steps", []):
                steps_sheet.write(step_row, 0, exec_data["execution_id"], cell_format)
                steps_sheet.write(step_row, 1, exec_data["test_id"], cell_format)
                steps_sheet.write(step_row, 2, step.get("step_number", 0), number_format)
                steps_sheet.write(step_row, 3, step.get("description", ""), cell_format)
                steps_sheet.write(step_row, 4, step.get("goal", ""), cell_format)

                # Action details
                steps_sheet.write(step_row, 5, step.get("action_type", ""), cell_format)
                steps_sheet.write(step_row, 6, step.get("action_target", ""), cell_format)
                steps_sheet.write(step_row, 7, step.get("coordinates_x", ""), number_format)
                steps_sheet.write(step_row, 8, step.get("coordinates_y", ""), number_format)
                steps_sheet.write(step_row, 9, step.get("coordinate_source", ""), cell_format)

                # SSIM verification
                ssim_score = step.get("ssim_score")
                if ssim_score is not None:
                    steps_sheet.write(step_row, 10, f"{ssim_score:.4f}", number_format)
                else:
                    steps_sheet.write(step_row, 10, "", cell_format)

                ssim_passed = step.get("ssim_passed")
                if ssim_passed is not None:
                    fmt = success_format if ssim_passed else failure_format
                    steps_sheet.write(step_row, 11, "PASS" if ssim_passed else "FAIL", fmt)
                else:
                    steps_sheet.write(step_row, 11, "", cell_format)

                steps_sheet.write(step_row, 12, step.get("ssim_threshold", ""), number_format)
                steps_sheet.write(step_row, 13, step.get("reference_image_name", ""), cell_format)

                # Learned solution
                used_learned = step.get("used_learned_solution")
                if used_learned is not None:
                    steps_sheet.write(step_row, 14, "Yes" if used_learned else "No", cell_format)
                else:
                    steps_sheet.write(step_row, 14, "", cell_format)

                # Status
                status = step.get("status", "pending")
                fmt = success_format if status == "success" else (failure_format if status in ["failure", "error"] else cell_format)
                steps_sheet.write(step_row, 15, status.upper(), fmt)

                steps_sheet.write(step_row, 16, step.get("duration_ms", 0), number_format)
                steps_sheet.write(step_row, 17, step.get("comparison_image_path", ""), cell_format)
                steps_sheet.write(step_row, 18, step.get("error_message", ""), cell_format)

                step_row += 1

    # ═══════════════════════════════════════════════════════════
    # PDF Generation
    # ═══════════════════════════════════════════════════════════

    def _generate_pdf(
        self,
        report_id: str,
        request: GenerateReportRequest,
        executions: List[Dict]
    ) -> ReportMetadata:
        """Generate PDF report."""
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch, mm
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                PageBreak, Image
            )
            from reportlab.graphics.shapes import Drawing
            from reportlab.graphics.charts.piecharts import Pie
            from reportlab.graphics.charts.barcharts import VerticalBarChart
        except ImportError:
            logger.error("reportlab not installed")
            raise ImportError("reportlab is required for PDF reports")

        filename = f"{report_id}.pdf"
        file_path = self.reports_dir / filename

        # Create document
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#00d4ff'),
            spaceAfter=12,
            alignment=1  # Center
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#00d4ff'),
            spaceBefore=20,
            spaceAfter=12
        )
        body_style = styles['Normal']

        # Content elements
        elements = []

        # Title
        elements.append(Paragraph(request.title or "Test Execution Report", title_style))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", body_style))
        elements.append(Spacer(1, 30))

        # Executive Summary
        elements.append(Paragraph("Executive Summary", heading_style))

        total = len(executions)
        passed = sum(1 for e in executions if e["status"] == "success")
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0

        summary_data = [
            ["Metric", "Value"],
            ["Total Executions", str(total)],
            ["Passed", str(passed)],
            ["Failed", str(failed)],
            ["Pass Rate", f"{pass_rate:.1f}%"]
        ]

        summary_table = Table(summary_data, colWidths=[200, 150])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#00d4ff')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#3a3a4e'))
        ]))
        elements.append(summary_table)

        # Pie chart
        if request.include_charts and total > 0:
            elements.append(Spacer(1, 20))

            drawing = Drawing(400, 200)
            pie = Pie()
            pie.x = 100
            pie.y = 25
            pie.width = 150
            pie.height = 150
            pie.data = [passed, failed]
            pie.labels = [f'Passed ({passed})', f'Failed ({failed})']
            pie.slices[0].fillColor = colors.HexColor('#00ff88')
            pie.slices[1].fillColor = colors.HexColor('#ff4444')
            drawing.add(pie)
            elements.append(drawing)

        elements.append(PageBreak())

        # Execution Details
        elements.append(Paragraph("Execution Details", heading_style))

        if executions:
            exec_data = [["Test ID", "Status", "Duration", "Steps", "Pass Rate"]]

            for exec_item in executions[:50]:  # Limit for PDF
                total_steps = exec_item.get("total_steps", 0)
                passed_steps = exec_item.get("passed_steps", 0)
                step_rate = f"{(passed_steps/total_steps*100):.0f}%" if total_steps > 0 else "N/A"
                duration = exec_item.get("duration_ms", 0)
                duration_str = f"{duration/1000:.1f}s" if duration else "N/A"

                exec_data.append([
                    exec_item["test_id"][:20],
                    exec_item["status"].upper(),
                    duration_str,
                    f"{passed_steps}/{total_steps}",
                    step_rate
                ])

            exec_table = Table(exec_data, colWidths=[120, 70, 70, 60, 70])
            exec_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#00d4ff')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#16213e')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#3a3a4e'))
            ]))
            elements.append(exec_table)

        # SSIM Results
        if request.include_ssim_details:
            elements.append(PageBreak())
            elements.append(Paragraph("SSIM Verification Results", heading_style))

            ssim_records = []
            for exec_item in executions:
                for step in exec_item.get("steps", []):
                    if step.get("ssim_score") is not None:
                        ssim_records.append({
                            "test_id": exec_item["test_id"],
                            "step": step["step_number"],
                            "score": step["ssim_score"],
                            "passed": step.get("ssim_passed", False)
                        })

            if ssim_records:
                ssim_data = [["Test ID", "Step", "SSIM Score", "Result"]]
                for rec in ssim_records[:100]:  # Limit
                    ssim_data.append([
                        rec["test_id"][:15],
                        str(rec["step"]),
                        f"{rec['score']:.4f}",
                        "PASS" if rec["passed"] else "FAIL"
                    ])

                ssim_table = Table(ssim_data, colWidths=[120, 50, 80, 60])
                ssim_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#00d4ff')),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#16213e')),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.white),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#3a3a4e'))
                ]))
                elements.append(ssim_table)

        # Step-by-Step Execution Details (Enhanced)
        if request.include_step_details:
            elements.append(PageBreak())
            elements.append(Paragraph("Step-by-Step Execution Details", heading_style))

            step_detail_style = ParagraphStyle(
                'StepDetail',
                parent=body_style,
                fontSize=9,
                textColor=colors.white,
                spaceAfter=4
            )

            for exec_item in executions[:10]:  # Limit for PDF size
                # Test case header
                elements.append(Spacer(1, 10))
                test_header = f"Test: {exec_item['test_id']} - {exec_item.get('test_title', 'N/A')}"
                elements.append(Paragraph(test_header, heading_style))

                # Execution info
                exec_info = f"Status: {exec_item['status'].upper()} | Learned Solution: {'Yes' if exec_item.get('use_learned') else 'No'}"
                elements.append(Paragraph(exec_info, step_detail_style))
                elements.append(Spacer(1, 8))

                # Steps table with all details
                for step in exec_item.get("steps", []):
                    step_data = [
                        ["Step", "Description", "Action", "Coordinates", "SSIM", "Result"],
                        [
                            str(step.get("step_number", 0)),
                            step.get("description", "")[:40],
                            f"{step.get('action_type', '')} {step.get('action_target', '')}",
                            f"({step.get('coordinates_x', '-')}, {step.get('coordinates_y', '-')}) [{step.get('coordinate_source', '')}]",
                            f"{step.get('ssim_score', 0):.4f}" if step.get('ssim_score') else "N/A",
                            "PASS" if step.get("ssim_passed") else ("FAIL" if step.get("ssim_passed") is False else "N/A")
                        ]
                    ]

                    step_table = Table(step_data, colWidths=[35, 100, 80, 100, 50, 45])
                    step_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a2a4e')),
                        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTSIZE', (0, 0), (-1, -1), 7),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#3a3a4e')),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#16213e'))
                    ]))
                    elements.append(step_table)

                    # Add comparison image if available and requested
                    if request.include_screenshots and step.get("comparison_image_path"):
                        comp_path = step.get("comparison_image_path")
                        if Path(comp_path).exists():
                            try:
                                elements.append(Spacer(1, 4))
                                img = Image(comp_path, width=400, height=150)
                                elements.append(img)
                                elements.append(Spacer(1, 4))
                            except Exception as img_err:
                                logger.debug(f"Could not add image: {img_err}")

                    elements.append(Spacer(1, 6))

                elements.append(Spacer(1, 15))

        # Build PDF
        doc.build(elements)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Build date range
        dates = [e["started_at"][:10] for e in executions if e.get("started_at")]
        date_range = f"{min(dates)} to {max(dates)}" if dates else None

        return ReportMetadata(
            report_id=report_id,
            filename=filename,
            format=ReportFormat.PDF,
            report_type=request.report_type,
            title=request.title or "Test Execution Report",
            description=request.description,
            executions_included=len(executions),
            date_range=date_range,
            test_ids_included=list(set(e["test_id"] for e in executions)),
            file_path=str(file_path),
            file_size_bytes=file_size,
            include_screenshots=request.include_screenshots,
            include_ssim_details=request.include_ssim_details,
            include_charts=request.include_charts
        )

    # ═══════════════════════════════════════════════════════════
    # Report Management
    # ═══════════════════════════════════════════════════════════

    def list_reports(self) -> List[Dict[str, Any]]:
        """List all generated reports."""
        return self.reports_metadata.get("reports", [])

    def get_report(self, report_id: str) -> Optional[ReportMetadata]:
        """Get report metadata by ID."""
        for report in self.reports_metadata.get("reports", []):
            if report["report_id"] == report_id:
                return ReportMetadata(**report)
        return None

    def get_report_path(self, report_id: str) -> Optional[Path]:
        """Get file path for a report."""
        metadata = self.get_report(report_id)
        if metadata:
            path = Path(metadata.file_path)
            if path.exists():
                return path
        return None

    def delete_report(self, report_id: str) -> bool:
        """Delete a report and its file."""
        try:
            # Find and remove from metadata
            for i, report in enumerate(self.reports_metadata.get("reports", [])):
                if report["report_id"] == report_id:
                    # Delete file
                    file_path = Path(report["file_path"])
                    if file_path.exists():
                        file_path.unlink()

                    # Remove from list
                    del self.reports_metadata["reports"][i]
                    self._save_metadata()

                    logger.info(f"Deleted report: {report_id}")
                    return True

            return False
        except Exception as e:
            logger.error(f"Failed to delete report {report_id}: {e}")
            return False

    def get_preview(self, report_id: str) -> Optional[ReportPreview]:
        """Get preview data for a report (for HTML display)."""
        metadata = self.get_report(report_id)
        if not metadata:
            return None

        # For Excel, we'd parse the file to generate preview
        # For PDF, we can't easily preview
        # This is a simplified preview

        history_service = get_test_history_service()
        result = history_service.list_executions(page=1, page_size=20)

        preview = ReportPreview(
            summary={
                "title": metadata.title,
                "generated_at": metadata.generated_at,
                "executions_included": metadata.executions_included,
                "format": metadata.format.value
            },
            executions_table=ReportPreviewTable(
                headers=["Test ID", "Status", "Duration", "Pass Rate"],
                rows=[
                    ReportPreviewRow(cells=[
                        e["test_id"],
                        e["status"],
                        f"{e.get('duration_ms', 0)}ms",
                        f"{e.get('pass_rate', 0):.1f}%"
                    ])
                    for e in result["executions"][:10]
                ]
            )
        )

        return preview


# ═══════════════════════════════════════════════════════════
# Singleton instance
# ═══════════════════════════════════════════════════════════

_report_generator: Optional[ReportGenerator] = None


def get_report_generator() -> ReportGenerator:
    """Get or create report generator singleton."""
    global _report_generator

    if _report_generator is None:
        _report_generator = ReportGenerator()

    return _report_generator
