import os
from typing import List, Tuple, Dict, Any, Optional
from google.oauth2.service_account import Credentials
import gspread
from dotenv import load_dotenv

load_dotenv()

class SheetsClient:
    def __init__(self):
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        sheet_id = os.getenv("SHEET_ID")
        if not creds_path:
            raise ValueError("Missing GOOGLE_APPLICATION_CREDENTIALS in .env")
        if not sheet_id:
            raise ValueError("Missing SHEET_ID in .env")

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
        self.client = gspread.authorize(creds)
        self.sheet_id = sheet_id

    def read_stops_and_vans(self) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        stops_ws = self.client.open_by_key(self.sheet_id).worksheet("Stops")
        vans_ws = self.client.open_by_key(self.sheet_id).worksheet("Vans")

        stops = stops_ws.get_all_records()
        vans = vans_ws.get_all_records()
        return stops, vans
    def _get_or_create_worksheet(self, title: str, rows: int = 1000, cols: int = 20):
        sh = self.client.open_by_key(self.sheet_id)
        try:
            ws = sh.worksheet(title)
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title=title, rows=str(rows), cols=str(cols))
        return ws

    def write_routes(
            self,
            routes_ws_name: str,
            routes: Dict[int, List[int]],
            van_ids: List[Any],
            stop_ids: List[Any],
            addresses: List[str],
            students: List[int],
            per_van_cost: Optional[Dict[int, float]] = None,
            total_cost: Optional[float] = None,
            cost_unit: Optional[str] = None,
            clear_first: bool = True,
    ) -> None:

        ws = self._get_or_create_worksheet(routes_ws_name)

        if clear_first:
            ws.clear()

        header = [
            "Van ID",
            "Stop Order",
            "Stop Index",
            "Stop ID",
            "Address",
            "Students",
            f"Van Route Cost ({cost_unit})" if cost_unit else "Van Route Cost",
        ]

        rows_to_write = [header]

        for v, route in routes.items():
            van_label = str(van_ids[v]) if v < len(van_ids) else f"Van{v + 1}"

            van_cost = ""
            if per_van_cost is not None and v in per_van_cost:
                van_cost = round(per_van_cost[v], 2)

            for order, stop_idx in enumerate(route):
                rows_to_write.append([
                    van_label,
                    order,
                    stop_idx,
                    stop_ids[stop_idx] if stop_idx < len(stop_ids) else "",
                    addresses[stop_idx] if stop_idx < len(addresses) else "",
                    students[stop_idx] if stop_idx < len(students) else "",
                    van_cost if order == 0 else "",  # show cost once per van
                ])

            rows_to_write.append([""] * len(header))

        if total_cost is not None:
            rows_to_write.append([
                "TOTAL",
                "",
                "",
                "",
                "",
                "",
                round(total_cost, 2),
            ])

        ws.update("A1", rows_to_write, value_input_option="RAW")