import datetime
import decimal
from typing import Optional

import re
from collections import OrderedDict

from rules import Columns, load_map


class Transaction:
    def __init__(self, date: datetime.date, description: str,
                 amount: decimal.Decimal, balance: decimal.Decimal,
                 bank_category: str = None) -> None:
        self._date = date
        self._description = description
        self._amount = amount
        self._balance = balance
        self._bank_category = bank_category

    @property
    def date(self) -> datetime.date:
        return self._date

    @property
    def description(self) -> str:
        return self._description

    @property
    def amount(self) -> decimal.Decimal:
        return self._amount

    @property
    def balance(self) -> decimal.Decimal:
        return self._balance

    @property
    def bank_category(self) -> str:
        return self._bank_category

    def __str__(self) -> str:
        return "Transaction on {}: amount {}, {}, "\
               "balance {}, provided category: {}".format(
                   self.date, self.amount, self.description, self.balance,
                   self.bank_category
               )

    def __repr__(self) -> str:
        return "Transaction('{}', {}, '{}', {}, '{}')".format(
            self.date, self.amount, self.description, self.balance,
            self.bank_category
        )


class ProcessedTransaction(Transaction):
    LONG_DESC_REGEX_TO_SHORT_DESC = load_map(
        from_column=Columns.long_desc_regex,
        to_column=Columns.short_desc
    )
    SHORT_DESC_TO_CATEGORY_MAP = load_map(
        from_column=Columns.short_desc,
        to_column=Columns.category
    )
    SHORT_DESC_TO_SUB_CATEGORY_MAP = load_map(
        from_column=Columns.short_desc,
        to_column=Columns.sub_category
    )
    SUB_CATEGORY_TO_CATEGORY_MAP = load_map(
        from_column=Columns.sub_category,
        to_column=Columns.category
    )
    BANK_CATEGORY_TO_CATEGORY_MAP = load_map(
        from_column=Columns.bank_category,
        to_column=Columns.category
    )
    BANK_CATEGORY_TO_SUB_CATEGORY_MAP = load_map(
        from_column=Columns.bank_category,
        to_column=Columns.sub_category
    )

    HOUSEHOLD_CATEGORIES = {
        "Household essentials", "Household nice-to-haves"
    }

    def __init__(self, date: datetime.date, description: str,
                 amount: decimal.Decimal, balance: decimal.Decimal,
                 bank_category: Optional[str]=None) -> None:
        mapped_description = self._map_description(description)
        super().__init__(date, mapped_description, amount, balance,
                         bank_category)

        self._sub_category = self._get_sub_category()
        self._category = self._get_category()

    @property
    def category(self) -> str:
        return self._category

    @property
    def sub_category(self) -> str:
        return self._sub_category

    @property
    def is_household_expense(self) -> Optional[bool]:
        return self._is_household_expense()

    def as_ordered_dict(self) -> OrderedDict:
        """ Omit balance from the view. """
        if isinstance(self.is_household_expense, bool):
            is_household_expense = "Yes" if self._is_household_expense() else "No"
        else:
            is_household_expense = ""

        return OrderedDict([
            ('description', self.description),
            ('amount', self.amount),
            ('category', self.category if self.category else ''),
            ('sub_category', self.sub_category if self.sub_category else ''),
            ('date', self.date),
            ('is_household_expense', is_household_expense),
            ('bank_category', self.bank_category if self.bank_category else ''),
        ])
        
    def _map_description(self, description: str) -> str:
        for desc_regex, short_desc in self.LONG_DESC_REGEX_TO_SHORT_DESC.items():
            if re.search(desc_regex, description):
                return short_desc
        return description

    def _get_category(self) -> Optional[str]:
        if self.bank_category in self.BANK_CATEGORY_TO_CATEGORY_MAP:
            return self.BANK_CATEGORY_TO_CATEGORY_MAP[self.bank_category]
        
        if self.sub_category in self.SUB_CATEGORY_TO_CATEGORY_MAP:
            return self.SUB_CATEGORY_TO_CATEGORY_MAP[self.sub_category]

        if self.description in self.SHORT_DESC_TO_CATEGORY_MAP:
            return self.SHORT_DESC_TO_CATEGORY_MAP[self.description]

        return None

    def _get_sub_category(self) -> Optional[str]:
        if self.bank_category in self.BANK_CATEGORY_TO_SUB_CATEGORY_MAP:
            return self.BANK_CATEGORY_TO_SUB_CATEGORY_MAP[self.bank_category]

        if self.description in self.SHORT_DESC_TO_SUB_CATEGORY_MAP:
            return self.SHORT_DESC_TO_SUB_CATEGORY_MAP[self.description]

        return None

    def _is_household_expense(self) -> Optional[bool]:
        if self.category in self.HOUSEHOLD_CATEGORIES:
            return True
        elif self.category:
            return False
        else:
            return None

    def __str__(self) -> str:
        return super().__str__() + \
            ". Category: {}, subcategory: {}, "\
            "household expense: {}".format(self.category, self.sub_category,
                                           self.is_household_expense)
