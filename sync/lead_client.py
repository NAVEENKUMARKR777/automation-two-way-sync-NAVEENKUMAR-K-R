import logging
from typing import Dict, List, Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from .config import GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_SHEET_ID, GOOGLE_SHEET_RANGE


logger = logging.getLogger(__name__)


LEAD_HEADERS = ["id", "name", "email", "status", "source", "task_id"]


class LeadTrackerClient:
    """Client for Google Sheets based Lead Tracker."""

    def __init__(self) -> None:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE,
            scopes=scopes,
        )
        self.service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        self.sheet_id = GOOGLE_SHEET_ID
        self.range_name = GOOGLE_SHEET_RANGE

    def _get_values(self) -> List[List[str]]:
        result = (
            self.service.spreadsheets()
            .values()
            .get(spreadsheetId=self.sheet_id, range=self.range_name)
            .execute()
        )
        return result.get("values", [])

    def list_leads(self) -> List[Dict[str, Any]]:
        """Return all leads as dicts, including their row numbers in the sheet."""
        values = self._get_values()
        if not values:
            return []

        headers = values[0]
        rows = values[1:]

        header_index = {h: i for i, h in enumerate(headers)}

        leads: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows, start=2):  # account for header row
            lead: Dict[str, Any] = {"_row": idx}
            for header in LEAD_HEADERS:
                col_idx = header_index.get(header)
                lead[header] = row[col_idx] if col_idx is not None and col_idx < len(row) else ""
            leads.append(lead)
        return leads

    def update_lead_fields(self, row: int, fields: Dict[str, Any]) -> None:
        """Update selected fields for a lead at a given row."""
        values = self._get_values()
        if not values or row - 1 >= len(values):
            logger.warning("Row %s not found in sheet while trying to update", row)
            return

        headers = values[0]
        row_values = values[row - 1]

        # Ensure row_values has enough columns
        if len(row_values) < len(headers):
            row_values = row_values + [""] * (len(headers) - len(row_values))

        for key, value in fields.items():
            if key not in headers:
                logger.warning("Header %s not present in sheet; skipping", key)
                continue
            idx = headers.index(key)
            row_values[idx] = value

        # Write back the entire row
        range_prefix = self.range_name.split("!")[0]
        update_range = f"{range_prefix}!A{row}:{chr(ord('A') + len(headers) - 1)}{row}"

        body = {"values": [row_values]}
        self.service.spreadsheets().values().update(
            spreadsheetId=self.sheet_id,
            range=update_range,
            valueInputOption="RAW",
            body=body,
        ).execute()


