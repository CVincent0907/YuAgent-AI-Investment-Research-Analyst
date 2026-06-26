"""
MCP Tool: Google Sheets Portfolio Operations
Wraps mcp_bridge calls for portfolio read/write via the mcp-gsheets MCP server.
Each function is marked as an MCP Tool for LangSmith traceability.

Sheet column layout (A → P):
    A  Ticker
    B  Quantity
    C  Avg Price
    D  Current Price       ← computed / manual, not LLM-managed
    E  Sector
    F  Target Weight
    G  Current Weight      ← computed / manual, not LLM-managed
    H  Thesis
    I  Thesis Status
    J  Risk Limit
    K  Expected CAGR
    L  Confidence Score
    M  Entry Date
    N  Last Review Date
    O  Next Review Date
    P  Notes
"""

import os
from langsmith import traceable
from src.mcp.mcp_bridge import run_mcp_tool

# ── Constants ─────────────────────────────────────────────────────────────────

_SHEET_TAB = "'YuAgent Current Portfolio'"
_SPREADSHEET_ID = lambda: os.getenv("PORTFOLIO_SPREADSHEET_ID")

# Maps every LLM-writable field name → its column letter in the sheet.
COLUMN_MAP: dict[str, str] = {
    "ticker":           "A",
    "quantity":         "B",
    "avg_price":        "C",
    "current_price":    "D",
    "sector":           "E",
    "target_weight":    "F",
    "current_weight":   "G",
    "thesis":           "H",
    "thesis_status":    "I",
    "risk_limit":       "J",
    "expected_cagr":    "K",
    "confidence_score": "L",
    "entry_date":       "M",
    "last_review_date": "N",
    "next_review_date": "O",
    "notes":            "P",
}

# Ordered list that defines the 16-column row written by `append`.
# Columns D (current_price) and G (current_weight) are intentionally left
# empty on append because they are computed / manually maintained.
_APPEND_COLUMN_ORDER = [
    "ticker",           # A
    "quantity",         # B
    "avg_price",        # C
    "current_price",    # D  — leave blank; populated externally
    "sector",           # E
    "target_weight",    # F
    "current_weight",   # G  — leave blank; populated externally
    "thesis",           # H
    "thesis_status",    # I
    "risk_limit",       # J
    "expected_cagr",    # K
    "confidence_score", # L
    "entry_date",       # M
    "last_review_date", # N
    "next_review_date", # O
    "notes",            # P
]


# ── READ ──────────────────────────────────────────────────────────────────────

@traceable(name="MCP Tool: Get Portfolio Data")
def get_portfolio_data() -> str:
    """
    MCP Tool — Reads all rows from the 'YuAgent Current Portfolio' Google Sheet tab.

    Returns:
        A string containing the sheet values or an MCP error message.
    """
    return run_mcp_tool(
        "google-sheets",
        "sheets_get_values",
        {
            "spreadsheetId": _SPREADSHEET_ID(),
            "range": f"{_SHEET_TAB}!A:P",
        },
    )


# ── APPEND (new row) ──────────────────────────────────────────────────────────

@traceable(name="MCP Tool: Append Portfolio Row")
def append_portfolio_row(
    ticker: str = "",
    quantity: str = "",
    avg_price: str = "",
    current_price: str = "",
    sector: str = "",
    target_weight: str = "",
    current_weight: str = "",
    thesis: str = "",
    thesis_status: str = "",
    risk_limit: str = "",
    expected_cagr: str = "",
    confidence_score: str = "",
    entry_date: str = "",
    last_review_date: str = "",
    next_review_date: str = "",
    notes: str = "",
) -> str:
    """
    MCP Tool — Appends a new portfolio row at the bottom of the sheet.

    Each argument maps directly to the corresponding column (A–P).
    Columns that are not supplied default to an empty string (cell left blank).

    Returns:
        A string result from the MCP server or an error message.
    """
    field_values = {
        "ticker": ticker,
        "quantity": quantity,
        "avg_price": avg_price,
        "current_price": current_price,
        "sector": sector,
        "target_weight": target_weight,
        "current_weight": current_weight,
        "thesis": thesis,
        "thesis_status": thesis_status,
        "risk_limit": risk_limit,
        "expected_cagr": expected_cagr,
        "confidence_score": confidence_score,
        "entry_date": entry_date,
        "last_review_date": last_review_date,
        "next_review_date": next_review_date,
        "notes": notes,
    }

    # Build the row in the exact column order A → P
    row = [field_values[col] for col in _APPEND_COLUMN_ORDER]

    return run_mcp_tool(
        "google-sheets",
        "sheets_append_values",
        {
            "spreadsheetId": _SPREADSHEET_ID(),
            "range": f"{_SHEET_TAB}!A:P",
            "values": [row],
            "insertDataOption": "INSERT_ROWS",
        },
    )


# ── UPDATE (targeted field patch on an existing row) ─────────────────────────

@traceable(name="MCP Tool: Update Portfolio Row")
def update_portfolio_row(
    row_number: int,
    ticker: str = None,
    quantity: str = None,
    avg_price: str = None,
    current_price: str = None,
    sector: str = None,
    target_weight: str = None,
    current_weight: str = None,
    thesis: str = None,
    thesis_status: str = None,
    risk_limit: str = None,
    expected_cagr: str = None,
    confidence_score: str = None,
    entry_date: str = None,
    last_review_date: str = None,
    next_review_date: str = None,
    notes: str = None,
) -> str:
    """
    MCP Tool — Updates specific fields of an existing row.

    Only fields with a non-None value are written; all other columns are left
    completely untouched, preventing accidental data loss.

    Args:
        row_number: The 1-based sheet row number to update (row 1 = header,
                    so data starts at row 2).
        ticker … notes: Pass only the fields you want to change. Any field
                        left as None will not be written.

    Returns:
        A string result from the MCP server or an error message.
    """
    if row_number < 2:
        return "Error: row_number must be >= 2 (row 1 is the header)."

    field_values = {
        "ticker": ticker,
        "quantity": quantity,
        "avg_price": avg_price,
        "current_price": current_price,
        "sector": sector,
        "target_weight": target_weight,
        "current_weight": current_weight,
        "thesis": thesis,
        "thesis_status": thesis_status,
        "risk_limit": risk_limit,
        "expected_cagr": expected_cagr,
        "confidence_score": confidence_score,
        "entry_date": entry_date,
        "last_review_date": last_review_date,
        "next_review_date": next_review_date,
        "notes": notes,
    }

    # Build a targeted batch update — one entry per non-None field
    updates = []
    for field, value in field_values.items():
        if value is not None:
            col_letter = COLUMN_MAP[field]
            cell = f"{_SHEET_TAB}!{col_letter}{row_number}"
            updates.append({"range": cell, "values": [[value]]})

    if not updates:
        return "Error: No fields provided to update. Pass at least one field value."

    return run_mcp_tool(
        "google-sheets",
        "sheets_batch_update_values",
        {
            "spreadsheetId": _SPREADSHEET_ID(),
            "data": updates,
        },
    )


# ── DELETE ────────────────────────────────────────────────────────────────────

@traceable(name="MCP Tool: Delete Portfolio Row")
def delete_portfolio_row(row_number: int) -> str:
    """
    MCP Tool — Physically removes a row from the portfolio sheet.

    Args:
        row_number: The 1-based sheet row number to delete (>= 2).

    Returns:
        A string result from the MCP server or an error message.
    """
    if row_number < 2:
        return "Error: row_number must be >= 2 (row 1 is the header)."

    row_range = f"{_SHEET_TAB}!{row_number}:{row_number}"
    return run_mcp_tool(
        "google-sheets",
        "sheets_delete_rows",
        {
            "spreadsheetId": _SPREADSHEET_ID(),
            "range": row_range,
        },
    )


# ── LEGACY COMPAT SHIM ────────────────────────────────────────────────────────
# Kept so existing query_entry.py dispatch still works while you migrate.

@traceable(name="MCP Tool: Update Portfolio Data (legacy)")
def update_portfolio_data(
    action: str = "append",
    row_number: int = None,
    ticker: str = None,
    quantity: str = None,
    avg_price: str = None,
    current_price: str = None,
    sector: str = None,
    target_weight: str = None,
    current_weight: str = None,
    thesis: str = None,
    thesis_status: str = None,
    risk_limit: str = None,
    expected_cagr: str = None,
    confidence_score: str = None,
    entry_date: str = None,
    last_review_date: str = None,
    next_review_date: str = None,
    notes: str = None,
    # old-style raw range kept for backward compat
    range: str = None,
    updates: list = None,
) -> str:
    """
    Legacy dispatcher — routes to the correct typed helper above.
    New code should call append_portfolio_row / update_portfolio_row /
    delete_portfolio_row directly.
    """
    _str = lambda v: "" if v is None else str(v)

    if action == "append":
        return append_portfolio_row(
            ticker=_str(ticker),
            quantity=_str(quantity),
            avg_price=_str(avg_price),
            current_price=_str(current_price),
            sector=_str(sector),
            target_weight=_str(target_weight),
            current_weight=_str(current_weight),
            thesis=_str(thesis),
            thesis_status=_str(thesis_status),
            risk_limit=_str(risk_limit),
            expected_cagr=_str(expected_cagr),
            confidence_score=_str(confidence_score),
            entry_date=_str(entry_date),
            last_review_date=_str(last_review_date),
            next_review_date=_str(next_review_date),
            notes=_str(notes),
        )

    elif action == "update":
        if row_number:
            return update_portfolio_row(
                row_number=int(row_number),
                ticker=ticker,
                quantity=quantity,
                avg_price=avg_price,
                current_price=current_price,
                sector=sector,
                target_weight=target_weight,
                current_weight=current_weight,
                thesis=thesis,
                thesis_status=thesis_status,
                risk_limit=risk_limit,
                expected_cagr=expected_cagr,
                confidence_score=confidence_score,
                entry_date=entry_date,
                last_review_date=last_review_date,
                next_review_date=next_review_date,
                notes=notes,
            )
        # fallback to raw range if caller supplied it the old way
        if range:
            return run_mcp_tool(
                "google-sheets",
                "sheets_update_values",
                {
                    "spreadsheetId": _SPREADSHEET_ID(),
                    "range": range,
                    "values": [[_str(ticker), _str(quantity), _str(avg_price),
                                _str(current_price), _str(sector)]],
                },
            )
        return "Error: update action requires row_number."

    elif action == "delete_row":
        if row_number:
            return delete_portfolio_row(int(row_number))
        if range:
            return run_mcp_tool(
                "google-sheets",
                "sheets_delete_rows",
                {"spreadsheetId": _SPREADSHEET_ID(), "range": range},
            )
        return "Error: delete_row action requires row_number."

    elif action == "clear":
        if not range:
            return "Error: clear action requires a range."
        return run_mcp_tool(
            "google-sheets",
            "sheets_clear_values",
            {"spreadsheetId": _SPREADSHEET_ID(), "range": range},
        )

    elif action == "batch_update":
        return run_mcp_tool(
            "google-sheets",
            "sheets_batch_update_values",
            {"spreadsheetId": _SPREADSHEET_ID(), "data": updates or []},
        )

    else:
        return (
            f"Error: Unknown action '{action}'. "
            "Use append | update | delete_row | clear | batch_update."
        )
