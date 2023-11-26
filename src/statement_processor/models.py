import dataclasses
import datetime
from enum import Enum
from typing import Sequence, Optional, Tuple


TransactionPrimaryKey = Tuple[datetime.date, str, float]


@dataclasses.dataclass(frozen=True)
class Transaction:
    date: datetime.date
    description: str
    amount: float
    account_id: str
    is_shared_expense: bool = False
    added_on: Optional[datetime.datetime] = None
    updated_on: Optional[datetime.datetime] = None

    @property
    def primary_key(self) -> TransactionPrimaryKey:
        return self.date, self.description, self.amount

    def same_primary_key(self, other: "Transaction") -> bool:
        return self.primary_key == other.primary_key


@dataclasses.dataclass(frozen=True)
class Statement:
    from_date: datetime.date
    to_date: datetime.date
    account_id: str
    transactions: Sequence[Transaction]


class TextFeatureType(str, Enum):
    SHORT_DESCRIPTION = "short_description"


@dataclasses.dataclass(frozen=True)
class TextFeature:
    name: TextFeatureType
    transaction_id: TransactionPrimaryKey
    value: str
    origin: str  # "manual" or "decision_tree_classifier_v1.2"
    added_on: Optional[datetime.datetime] = None

    def similar(self, other: "TextFeature") -> bool:
        return (
            self.name == other.name
            and self.transaction_id == other.transaction_id
            and self.value == other.value
            and self.origin == other.origin
        )
