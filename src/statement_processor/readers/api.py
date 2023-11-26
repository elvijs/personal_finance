import datetime
from abc import ABC, abstractmethod
from typing import Tuple, Union

from statement_processor.models import Statement


class StatementReader(ABC):
    @abstractmethod
    def process(self) -> Statement:
        """Get a statement representing the file's contents"""


FromToValue = Tuple[datetime.date, datetime.date]
AccountValue = str
DateValue = datetime.date
DescriptionValue = str
AmountValue = float
BalanceValue = float
ParsedValue = Union[
    FromToValue,
    AccountValue,
    DateValue,
    DescriptionValue,
    AmountValue,
    BalanceValue,
]
StartEnd = Tuple[datetime.date, datetime.date]
