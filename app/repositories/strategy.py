import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict

from filelock import FileLock


class StorageStrategy(ABC):
    @abstractmethod
    def read(self) -> List[Dict]: ...

    @abstractmethod
    def write(self, rows: List[Dict]) -> None: ...

    @abstractmethod
    def init_file(self) -> None: ...


class CSVStorageStrategy(StorageStrategy):
    def __init__(self, file_path: Path, fields: List[str]):
        self.file_path = file_path
        self.fields = fields
        self.lock_path = str(self.file_path) + ".lock"

    def read(self) -> List[Dict]:
        if not self.file_path.exists():
            return []
        with open(self.file_path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def write(self, rows: List[Dict]) -> None:
        with FileLock(self.lock_path):
            with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writeheader()
                writer.writerows(rows)

    def init_file(self) -> None:
        needs_init = not self.file_path.exists()
        if not needs_init:
            with open(self.file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header != self.fields:
                    needs_init = True

        if needs_init:
            with open(self.file_path, "w", newline="", encoding="utf-8") as f:
                csv.DictWriter(f, fieldnames=self.fields).writeheader()


class JSONStorageStrategy(StorageStrategy):
    """Example of another strategy following OCP."""
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.lock_path = str(self.file_path) + ".lock"

    def read(self) -> List[Dict]:
        if not self.file_path.exists():
            return []
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write(self, rows: List[Dict]) -> None:
        with FileLock(self.lock_path):
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=4)

    def init_file(self) -> None:
        if not self.file_path.exists():
            self.write([])
