from __future__ import annotations

"""
TableChunker — converts CSV / XLSX rows into text chunks.

Strategy:
  - Group rows into batches of `rows_per_chunk` (default 10).
  - Each chunk is formatted as CSV text with the header repeated so the
    chunk is self-contained and readable by the LLM.
  - Remaining partial batch is always included.

Usage:
    chunker = TableChunker()
    chunks = chunker.chunk_csv(csv_text, rows_per_chunk=10)
"""

import csv
import io
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_DEFAULT_ROWS_PER_CHUNK = 10


@dataclass
class TableChunk:
    """A batch of rows from a CSV/XLSX file formatted as CSV text."""
    text: str
    row_start: int       # 1-based, first data row in this chunk
    row_end: int         # 1-based, last data row in this chunk
    extra: dict = field(default_factory=dict)   # e.g. {"sheet": "Sheet1"}


class TableChunker:
    """
    Stateless CSV/XLSX chunker — no DI needed.

    Methods:
        chunk_csv(csv_text, rows_per_chunk)   → list[TableChunk]
        chunk_xlsx_sheet(sheet_text, ...)     → list[TableChunk]  (same format)
    """

    def chunk_csv(
        self,
        csv_text: str,
        rows_per_chunk: int = _DEFAULT_ROWS_PER_CHUNK,
        extra: dict | None = None,
    ) -> list[TableChunk]:
        """
        Split raw CSV text into TableChunk objects.

        The header row is prepended to each chunk so it is self-contained.
        Empty rows are skipped.
        """
        reader = csv.reader(io.StringIO(csv_text))
        rows = [r for r in reader if any(cell.strip() for cell in r)]
        if not rows:
            return []

        header = rows[0]
        data_rows = rows[1:]

        if not data_rows:
            logger.debug("CSV has header but no data rows")
            return []

        chunks = []
        for batch_start in range(0, len(data_rows), rows_per_chunk):
            batch = data_rows[batch_start: batch_start + rows_per_chunk]
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(header)
            writer.writerows(batch)
            text = buf.getvalue().strip()

            row_start = batch_start + 1         # 1-based data row number
            row_end = batch_start + len(batch)

            chunks.append(TableChunk(
                text=text,
                row_start=row_start,
                row_end=row_end,
                extra=extra or {},
            ))

        logger.debug(
            "TableChunker: %d data rows → %d chunks (rows_per_chunk=%d)",
            len(data_rows), len(chunks), rows_per_chunk,
        )
        return chunks

    def chunk_xlsx_sheet(
        self,
        sheet_text: str,
        sheet_name: str = "",
        rows_per_chunk: int = _DEFAULT_ROWS_PER_CHUNK,
    ) -> list[TableChunk]:
        """
        Same as chunk_csv but tags each chunk with the sheet name.
        The sheet_text is expected to be CSV-formatted output from IngestHelper.
        """
        extra = {"sheet": sheet_name} if sheet_name else {}
        return self.chunk_csv(sheet_text, rows_per_chunk=rows_per_chunk, extra=extra)
