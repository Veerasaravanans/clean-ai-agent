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

from backend.models.enums import VerificationType, CleanupType, CleanupTrigger
from backend.models.results import CropRegion, StepVerificationConfig, StepCleanupConfig

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

        # NEW: Cleanup columns
        cleanup_type_col = self._find_column(headers, [
            'cleanup type', 'cleanup_type', 'cleanup', 'post-processing'
        ])
        cleanup_trigger_col = self._find_column(headers, [
            'cleanup trigger', 'cleanup_trigger', 'when to cleanup', 'cleanup_when'
        ])
        reverse_steps_col = self._find_column(headers, [
            'reverse steps', 'reverse_steps', 'reverse', 'undo steps'
        ])
        reverse_count_col = self._find_column(headers, [
            'reverse count', 'reverse_count', 'steps to reverse', 'undo count'
        ])
        ai_driven_cleanup_col = self._find_column(headers, [
            'ai driven cleanup', 'ai_driven_cleanup', 'ai cleanup', 'ai_cleanup'
        ])
        ai_context_col = self._find_column(headers, [
            'ai context', 'ai_context', 'cleanup context', 'ai cleanup context'
        ])
        close_dialog_col = self._find_column(headers, [
            'close dialog first', 'close_dialog_first', 'close dialog', 'dialog_close'
        ])
        dialog_button_col = self._find_column(headers, [
            'dialog close button', 'dialog_close_button', 'close button', 'dialog button'
        ])
        restore_components_col = self._find_column(headers, [
            'restore components', 'restore_components', 'components', 'restore_what'
        ])
        fallback_cleanup_col = self._find_column(headers, [
            'fallback cleanup', 'fallback_cleanup', 'backup cleanup', 'fallback'
        ])

        # NEW: Post Condition column (raw ADB intent commands for end-of-test cleanup)
        post_condition_col = self._find_column(headers, [
            'post condition', 'post_condition', 'postcondition', 'post-condition',
            'post conditions', 'post_conditions', 'cleanup intent', 'cleanup_intent'
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

                    # NEW: Parse post condition (raw ADB intents, semicolon-separated)
                    post_condition_str = self._get_cell_value(row, post_condition_col)
                    post_condition_intents = self._parse_post_condition(post_condition_str)

                    test_cases[current_test_id] = {
                        "test_id": current_test_id,
                        "title": title or "",
                        "component": component,
                        "type": test_type,
                        "steps": [],
                        "step_verification_configs": [],  # NEW: Per-step verification config
                        "step_cleanup_configs": [],  # NEW: Per-step cleanup config
                        "post_condition_intents": post_condition_intents,  # NEW: Raw ADB intents
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

                # NEW: Parse cleanup config for this step
                cleanup_type_str = self._get_cell_value(row, cleanup_type_col)
                cleanup_trigger_str = self._get_cell_value(row, cleanup_trigger_col)
                reverse_steps_str = self._get_cell_value(row, reverse_steps_col)
                reverse_count_str = self._get_cell_value(row, reverse_count_col)
                ai_driven_cleanup_str = self._get_cell_value(row, ai_driven_cleanup_col)
                ai_context_str = self._get_cell_value(row, ai_context_col)
                close_dialog_str = self._get_cell_value(row, close_dialog_col)
                dialog_button_str = self._get_cell_value(row, dialog_button_col)
                restore_components_str = self._get_cell_value(row, restore_components_col)
                fallback_cleanup_str = self._get_cell_value(row, fallback_cleanup_col)

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

                    # Parse and add cleanup config for this step
                    cleanup_config = self._parse_cleanup_config(
                        cleanup_type_str,
                        cleanup_trigger_str,
                        reverse_steps_str,
                        reverse_count_str,
                        ai_driven_cleanup_str,
                        ai_context_str,
                        close_dialog_str,
                        dialog_button_str,
                        restore_components_str,
                        fallback_cleanup_str
                    )
                    test_cases[current_test_id]["step_cleanup_configs"].append(
                        cleanup_config.to_dict()
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

    def _parse_cleanup_config(
        self,
        cleanup_type_str: Optional[str],
        cleanup_trigger_str: Optional[str],
        reverse_steps_str: Optional[str],
        reverse_count_str: Optional[str],
        ai_driven_cleanup_str: Optional[str],
        ai_context_str: Optional[str],
        close_dialog_str: Optional[str],
        dialog_button_str: Optional[str],
        restore_components_str: Optional[str],
        fallback_cleanup_str: Optional[str]
    ) -> StepCleanupConfig:
        """
        Parse cleanup configuration from Excel columns.

        Args:
            cleanup_type_str: Value from "Cleanup Type" column
            cleanup_trigger_str: Value from "Cleanup Trigger" column
            reverse_steps_str: Value from "Reverse Steps" column
            reverse_count_str: Value from "Reverse Count" column
            ai_driven_cleanup_str: Value from "AI Driven Cleanup" column
            ai_context_str: Value from "AI Context" column
            close_dialog_str: Value from "Close Dialog First" column
            dialog_button_str: Value from "Dialog Close Button" column
            restore_components_str: Value from "Restore Components" column
            fallback_cleanup_str: Value from "Fallback Cleanup" column

        Returns:
            StepCleanupConfig instance
        """
        # Parse cleanup type
        cleanup_type = self._parse_cleanup_type(cleanup_type_str)

        # Parse cleanup trigger
        cleanup_trigger = self._parse_cleanup_trigger(cleanup_trigger_str)

        # Parse boolean fields
        reverse_steps = self._parse_boolean(reverse_steps_str, default=False)
        ai_driven = self._parse_boolean(ai_driven_cleanup_str, default=False)
        close_dialog_first = self._parse_boolean(close_dialog_str, default=False)

        # Parse reverse count
        reverse_count = None
        if reverse_count_str:
            try:
                reverse_count = int(reverse_count_str)
            except ValueError:
                logger.warning(f"Invalid reverse_count value: {reverse_count_str}")

        # Parse restore components (comma-separated)
        restore_components = None
        if restore_components_str:
            restore_components = [c.strip() for c in restore_components_str.split(",") if c.strip()]

        # Parse fallback cleanup type
        fallback_cleanup_type = self._parse_cleanup_type(fallback_cleanup_str)
        if fallback_cleanup_type == CleanupType.NONE:
            fallback_cleanup_type = CleanupType.RETURN_HOME  # Default fallback

        return StepCleanupConfig(
            cleanup_type=cleanup_type,
            cleanup_trigger=cleanup_trigger,
            reverse_steps=reverse_steps,
            reverse_count=reverse_count,
            ai_driven=ai_driven,
            ai_context=ai_context_str,
            fallback_cleanup_type=fallback_cleanup_type,
            close_dialog_first=close_dialog_first,
            dialog_close_button_text=dialog_button_str,
            restore_specific_components=restore_components
        )

    def _parse_cleanup_type(self, value: Optional[str]) -> CleanupType:
        """
        Parse CleanupType from Excel value.

        Args:
            value: Raw Excel cell value

        Returns:
            CleanupType enum
        """
        if not value:
            return CleanupType.NONE

        value_lower = value.lower().strip()

        if not value_lower or "none" in value_lower or "skip" in value_lower:
            return CleanupType.NONE

        # CRITICAL: Check compound types FIRST (before simple types)
        # "reverse and home" contains both "reverse" and "home" — must match before either
        if "reverse and home" in value_lower or "reverse + home" in value_lower or "reverse_and_home" in value_lower:
            return CleanupType.REVERSE_AND_HOME
        elif "close and reboot" in value_lower or "close + reboot" in value_lower or "close_and_reboot" in value_lower:
            return CleanupType.CLOSE_AND_REBOOT
        elif "factory reset" in value_lower or "factory" in value_lower or "wipe" in value_lower:
            return CleanupType.FACTORY_RESET
        elif "ai driven" in value_lower or "ai_driven" in value_lower or "auto" in value_lower:
            return CleanupType.AI_DRIVEN
        # Simple types (checked AFTER compound types)
        elif "return home" in value_lower or "return_home" in value_lower or "home" in value_lower or "press home" in value_lower:
            return CleanupType.RETURN_HOME
        elif "reverse action" in value_lower or "reverse_action" in value_lower or "reverse" in value_lower or "undo" in value_lower:
            return CleanupType.REVERSE_ACTION
        elif "restore state" in value_lower or "restore_state" in value_lower or "restore" in value_lower:
            return CleanupType.RESTORE_STATE
        elif "close dialog" in value_lower or "close_dialog" in value_lower or "close" in value_lower or "dismiss" in value_lower:
            return CleanupType.CLOSE_DIALOG
        elif "reboot" in value_lower or "restart" in value_lower:
            return CleanupType.REBOOT
        else:
            logger.warning(f"Unknown cleanup type: {value}, defaulting to NONE")
            return CleanupType.NONE

    def _parse_cleanup_trigger(self, value: Optional[str]) -> CleanupTrigger:
        """
        Parse CleanupTrigger from Excel value.

        Args:
            value: Raw Excel cell value

        Returns:
            CleanupTrigger enum
        """
        if not value:
            return CleanupTrigger.END_OF_TEST  # Default

        value_lower = value.lower().strip()

        # Map common variations to enum values
        if "after step" in value_lower or "after each step" in value_lower or "per step" in value_lower:
            return CleanupTrigger.AFTER_STEP
        elif "end of test" in value_lower or "end" in value_lower or "final" in value_lower:
            return CleanupTrigger.END_OF_TEST
        elif "both" in value_lower or "always both" in value_lower or "step and test" in value_lower:
            return CleanupTrigger.BOTH
        elif "on failure" in value_lower or "if fail" in value_lower or "failure only" in value_lower:
            return CleanupTrigger.ON_FAILURE
        elif "always" in value_lower or "unconditional" in value_lower:
            return CleanupTrigger.ALWAYS
        else:
            logger.warning(f"Unknown cleanup trigger: {value}, defaulting to END_OF_TEST")
            return CleanupTrigger.END_OF_TEST

    def _parse_boolean(self, value: Optional[str], default: bool = False) -> bool:
        """
        Parse boolean from Excel value.

        Args:
            value: Raw Excel cell value
            default: Default value if parsing fails

        Returns:
            Boolean value
        """
        if not value:
            return default

        value_lower = value.lower().strip()

        # True values
        if value_lower in ["true", "yes", "y", "1", "on", "enabled", "enable"]:
            return True
        # False values
        elif value_lower in ["false", "no", "n", "0", "off", "disabled", "disable"]:
            return False
        else:
            logger.warning(f"Cannot parse boolean from: {value}, using default: {default}")
            return default

    def _parse_post_condition(self, value: Optional[str]) -> List[str]:
        """
        Parse post condition ADB intent commands from Excel value.

        Format: "intent1;intent2;intent3" (semicolon-separated)
        Each intent is a raw ADB command (e.g., "am start -a android.intent.action.MAIN")

        Args:
            value: Raw Excel cell value (semicolon-separated ADB commands)

        Returns:
            List of ADB intent command strings (empty list if none)
        """
        if not value:
            return []

        intents = []
        for part in value.split(";"):
            intent = part.strip()
            if intent:
                intents.append(intent)

        if intents:
            logger.info(f"   Post condition intents: {len(intents)} commands parsed")
            for i, intent in enumerate(intents):
                logger.info(f"     Intent {i+1}: {intent}")

        return intents

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