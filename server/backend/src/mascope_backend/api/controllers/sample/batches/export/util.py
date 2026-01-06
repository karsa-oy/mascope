"""
Excel utility functions for batch export operations.
"""

from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet


def auto_adjust_column_width(
    worksheet: Worksheet,
    max_width: int = 50,
    padding: int = 2,
) -> None:
    """
    Auto-adjust column widths based on content length.

    Iterates through all columns in the worksheet and sets width based on
    the longest cell content, with configurable maximum width and padding.

    :param worksheet: OpenPyXL worksheet to adjust
    :param max_width: Maximum column width to prevent excessively wide columns
    :param padding: Extra padding characters to add to calculated width
    """
    for column in worksheet.columns:
        column_letter = get_column_letter(column[0].column)
        max_length = 0

        for cell in column:
            if cell.value is not None:
                try:
                    cell_length = len(str(cell.value))
                    max_length = max(max_length, cell_length)
                except (TypeError, AttributeError):
                    # Skip cells with problematic values
                    continue

        # Apply width with padding, capped at max_width
        adjusted_width = min(max_length + padding, max_width)
        worksheet.column_dimensions[column_letter].width = adjusted_width
