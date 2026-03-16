"""Auto-generated backend module."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DataRecord:
    """Data record model."""
    id: Optional[int] = None
    name: str = ""
    data: Dict[str, Any] = None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.created_at is None:
            self.created_at = datetime.now()


class Backend:
    """Backend storage class."""
    
    def __init__(self):
        self.records: List[DataRecord] = []
        self._next_id = 1
    
    def create(self, name: str, data: Dict[str, Any]) -> DataRecord:
        """Create a new record."""
        record = DataRecord(
            id=self._next_id,
            name=name,
            data=data
        )
        self.records.append(record)
        self._next_id += 1
        return record
    
    def read(self, record_id: int) -> Optional[DataRecord]:
        """Read a record by ID."""
        for record in self.records:
            if record.id == record_id:
                return record
        return None
    
    def update(self, record_id: int, data: Dict[str, Any]) -> Optional[DataRecord]:
        """Update a record."""
        record = self.read(record_id)
        if record:
            record.data.update(data)
        return record
    
    def delete(self, record_id: int) -> bool:
        """Delete a record."""
        for i, record in enumerate(self.records):
            if record.id == record_id:
                self.records.pop(i)
                return True
        return False
    
    def list_all(self) -> List[DataRecord]:
        """List all records."""
        return self.records


if __name__ == "__main__":
    backend = Backend()
    record = backend.create("test", {"key": "value"})
    print(f"Created: {record}")
    print(f"Read: {backend.read(record.id)}")
