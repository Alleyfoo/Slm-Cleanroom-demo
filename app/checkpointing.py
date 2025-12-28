import csv
from pathlib import Path
from typing import Dict, Iterable, Set


class Checkpointer:
    """CSV-based checkpointing for idempotent batch processing."""

    def __init__(self, output_path: Path, error_path: Path, id_field: str = "id", fieldnames: Iterable[str] = ()):
        self.output_path = output_path
        self.error_path = error_path
        self.id_field = id_field
        self.fieldnames = list(fieldnames)
        self._processed: Set[str] = set()
        self._load_processed()

    def _load_processed(self) -> None:
        if not self.output_path.exists():
            return
        with self.output_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if self.id_field in row and row[self.id_field]:
                    self._processed.add(str(row[self.id_field]))

    def is_processed(self, row_id: str) -> bool:
        return str(row_id) in self._processed

    def append_row(self, row: Dict) -> None:
        is_new = not self.output_path.exists()
        with self.output_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames or row.keys())
            if is_new:
                writer.writeheader()
            writer.writerow(row)
        if self.id_field in row:
            self._processed.add(str(row[self.id_field]))

    def append_error(self, row_id: str, error: str, text: str) -> None:
        is_new = not self.error_path.exists()
        with self.error_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[self.id_field, "error", "text"])
            if is_new:
                writer.writeheader()
            writer.writerow({self.id_field: row_id, "error": error, "text": text})
