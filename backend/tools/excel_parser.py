"""
excel_parser.py - Excel Test Case Parser

Parses test case Excel files and extracts test cases with steps.
Handles multi-row format where steps are in separate rows.

DYNAMIC VERIFICATION SUPPORT:
- Parses "Verification Type" column for verification method
- Parses "What Needs to Be Verified" column for verification details
- Supports: Image verification, OCR, Partial image, No verification
"""

import logging
import re
from typing import List, Dict, Optional, Any
from pathlib import Path
import openpyxl

from backend.models.enums import VerificationType
from backend.models.results import CropRegion, StepVerificationConfig

logger = logging.getLogger(__name__)


class ExcelParser:
    """Parse test cases from Excel files."""
    
    def __init__(self):
        """Initialize parser."""
        self.current_file = None
        self.current_sheet = None
    
    def parse_test_cases(self, excel_path: str) -> List[Dict]:
        """
        Parse test cases from Excel file.
        
        Args:
            excel_path: Path to Excel file
            
        Returns:
            List of test case dictionaries
        """
        excel_path = Path(excel_path)
        
        if not excel_path.exists():
            logger.error(f"❌ Excel file not found: {excel_path}")
            return []
        
        logger.info(f"📖 Parsing Excel: {excel_path.name}")
        
        try:
            wb = openpyxl.load_workbook(excel_path)
            sheet = wb.active
            
            self.current_file = excel_path.name
            self.current_sheet = sheet.title
            
            # Get headers
            headers = self._get_headers(sheet)
            
            # Parse test cases
            test_cases = self._parse_rows(sheet, headers)
            
            logger.info(f"✅ Parsed {len(test_cases)} test cases from {excel_path.name}")
            
            return test_cases
            
        except Exception as e:
            logger.error(f"❌ Parse error: {e}")
            return []
    
    def _get_headers(self, sheet) -> Dict[str, int]:
        """
        Extract column headers and their indices.
        
        Returns:
            Dict mapping column name to index (0-based)
        """
        headers = {}
        
        for idx, cell in enumerate(sheet[1]):
            if cell.value:
                # Normalize header name
                header_name = str(cell.value).strip().lower()
                headers[header_name] = idx
        
        logger.debug(f"   Headers: {list(headers.keys())}")
        
        return headers
    
    def _parse_rows(self, sheet, headers: Dict[str, int]) -> List[Dict]:
        """
        Parse all rows and group by test case ID.

        Args:
            sheet: Excel sheet
            headers: Header mapping

        Returns:
            List of test cases with verification configs
        """
        test_cases = {}
        current_test_id = None

        # Map header variations to standard names
        id_col = self._find_column(headers, ['id', 'test id', 'test_id'])
        title_col = self._find_column(headers, ['title', 'test title', 'name'])
        step_num_col = self._find_column(headers, ['step', '#', 'step #', 'step number'])
        desc_col = self._find_column(headers, ['description', 'step description', 'desc'])
        expected_col = self._find_column(headers, ['expected result', 'expected', 'expected_result'])
        type_col = self._find_column(headers, ['type', 'test type'])

        # NEW: Verification columns
        verification_type_col = self._find_column(headers, [
            'verification type', 'verification_type', 'verify type', 'verify_type'
        ])
        what_to_verify_col = self._find_column(headers, [
            'what needs to be verified', 'what to verify', 'verify what',
            'verification details', 'verify details', 'what_to_verify'
        ])

        for row_idx in range(2, sheet.max_row + 1):
            row = sheet[row_idx]

            # Get test ID (if present in this row)
            test_id = self._get_cell_value(row, id_col)
            if test_id:
                current_test_id = test_id

                # Start new test case
                if current_test_id not in test_cases:
                    title = self._get_cell_value(row, title_col)
                    test_type = self._get_cell_value(row, type_col) or "Test Case"

                    # Extract component from title (before colon)
                    component = "Unknown"
                    if title and ":" in title:
                        component = title.split(":")[0].strip()

                    test_cases[current_test_id] = {
                        "test_id": current_test_id,
                        "title": title or "",
                        "component": component,
                        "type": test_type,
                        "steps": [],
                        "step_verification_configs": [],  # NEW: Per-step verification config
                        "description": title or ""  # Use title as description
                    }

            # Get step details
            if current_test_id:
                step_num = self._get_cell_value(row, step_num_col)
                step_desc = self._get_cell_value(row, desc_col)
                step_expected = self._get_cell_value(row, expected_col)

                # NEW: Parse verification config for this step
                verification_type_str = self._get_cell_value(row, verification_type_col)
                what_to_verify_str = self._get_cell_value(row, what_to_verify_col)

                if step_num and step_desc:
                    step_text = f"Step {step_num}: {step_desc}"
                    if step_expected:
                        step_text += f" (Expected: {step_expected})"

                    test_cases[current_test_id]["steps"].append(step_text)

                    # Parse and add verification config for this step
                    verification_config = self._parse_verification_config(
                        verification_type_str,
                        what_to_verify_str
                    )
                    test_cases[current_test_id]["step_verification_configs"].append(
                        verification_config.to_dict()
                    )

        # Convert to list and add expected field
        result = []
        for test_id, test_case in test_cases.items():
            # Add overall expected result (last step's expected)
            if test_case["steps"]:
                # Extract last expected from last step
                last_step = test_case["steps"][-1]
                if "(Expected:" in last_step:
                    expected = last_step.split("(Expected:")[1].rstrip(")")
                    test_case["expected"] = expected.strip()
                else:
                    test_case["expected"] = "Test completes successfully"
            else:
                test_case["expected"] = "Test completes successfully"

            result.append(test_case)

        return result

    def _parse_verification_config(
        self,
        verification_type_str: Optional[str],
        what_to_verify_str: Optional[str]
    ) -> StepVerificationConfig:
        """
        Parse verification configuration from Excel columns.

        Args:
            verification_type_str: Value from "Verification Type" column
            what_to_verify_str: Value from "What Needs to Be Verified" column

        Returns:
            StepVerificationConfig instance
        """
        # Determine verification type
        v_type = VerificationType.from_excel_value(verification_type_str or "")

        config = StepVerificationConfig(verification_type=v_type)

        if not what_to_verify_str:
            return config

        # Parse based on verification type
        if v_type == VerificationType.OCR:
            # Parse comma-separated texts, handling quoted strings
            config.expected_texts = self._parse_ocr_texts(what_to_verify_str)

        elif v_type == VerificationType.PARTIAL_IMAGE:
            # Parse crop regions: "region_name: x1,y1,x2,y2; region2: x1,y1,x2,y2"
            config.crop_regions = self._parse_crop_regions(what_to_verify_str)

        elif v_type == VerificationType.IMAGE:
            # Optional: reference image name override
            if what_to_verify_str.strip():
                config.reference_image_name = what_to_verify_str.strip()

        # No verification = no additional parsing needed

        return config

    def _parse_ocr_texts(self, text_str: str) -> List[str]:
        """
        Parse semicolon-separated texts for OCR verification.
        Handles quoted strings with semicolons inside.

        Format: Text1; Text2; Text3
        ALL texts must be found for verification to pass.

        Examples:
            "Settings; Bluetooth; WiFi" -> ["Settings", "Bluetooth", "WiFi"]
            "Bluetooth; Settings; Available devices" -> ["Bluetooth", "Settings", "Available devices"]
            '"Hi; how are you?"; Settings' -> ["Hi; how are you?", "Settings"]

        Args:
            text_str: Raw string from Excel

        Returns:
            List of expected texts
        """
        texts = []
        # Regex to match quoted strings or unquoted segments (semicolon-separated)
        pattern = r'"([^"]+)"|([^;]+)'
        matches = re.findall(pattern, text_str)

        for match in matches:
            # match is tuple (quoted, unquoted)
            text = match[0] if match[0] else match[1]
            text = text.strip()
            if text:
                texts.append(text)

        return texts

    def _parse_crop_regions(self, regions_str: str) -> List[CropRegion]:
        """
        Parse crop regions from string format.

        Format: "region_name: x1,y1,x2,y2; region2: x1,y1,x2,y2"

        Args:
            regions_str: Raw string from Excel

        Returns:
            List of CropRegion instances
        """
        regions = []

        # Split by semicolon for multiple regions
        parts = regions_str.split(";")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check for "name: coords" format
            if ":" in part:
                name_coords = part.split(":", 1)
                name = name_coords[0].strip()
                coords_str = name_coords[1].strip()
            else:
                # No name provided, use default
                name = f"region_{len(regions) + 1}"
                coords_str = part

            region = CropRegion.from_string(name, coords_str)
            if region.is_valid():
                regions.append(region)
            else:
                logger.warning(f"Invalid crop region coordinates: {part}")

        return regions
    
    def _find_column(self, headers: Dict[str, int], names: List[str]) -> Optional[int]:
        """
        Find column index by trying multiple possible names.
        
        Args:
            headers: Header mapping
            names: List of possible column names
            
        Returns:
            Column index or None
        """
        for name in names:
            if name.lower() in headers:
                return headers[name.lower()]
        return None
    
    def _get_cell_value(self, row, col_idx: Optional[int]) -> Optional[str]:
        """
        Get cell value safely.
        
        Args:
            row: Excel row
            col_idx: Column index
            
        Returns:
            Cell value as string or None
        """
        if col_idx is None or col_idx >= len(row):
            return None
        
        value = row[col_idx].value
        
        if value is None:
            return None
        
        # Convert to string and clean
        value_str = str(value).strip()
        
        # Remove excess whitespace
        value_str = " ".join(value_str.split())
        
        return value_str if value_str else None
    
    def parse_multiple_files(self, excel_dir: str, pattern: str = "*.xlsx") -> List[Dict]:
        """
        Parse all Excel files in directory.
        
        Args:
            excel_dir: Directory containing Excel files
            pattern: File pattern (default: *.xlsx)
            
        Returns:
            Combined list of all test cases
        """
        excel_dir = Path(excel_dir)
        
        if not excel_dir.exists():
            logger.error(f"❌ Directory not found: {excel_dir}")
            return []
        
        all_test_cases = []
        excel_files = list(excel_dir.glob(pattern))
        
        logger.info(f"📂 Found {len(excel_files)} Excel files in {excel_dir}")
        
        for excel_file in excel_files:
            test_cases = self.parse_test_cases(str(excel_file))
            all_test_cases.extend(test_cases)
        
        logger.info(f"✅ Total test cases parsed: {len(all_test_cases)}")
        
        return all_test_cases