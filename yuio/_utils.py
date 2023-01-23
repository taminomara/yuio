import enum
import re
import typing as _t

_TO_DASH_CASE_RE = re.compile(
    r'(?<!^)((?=[A-Z]([^A-Z]|$))|(?<=\d)(?=[A-Z])|(?<!\d)(?=\d))'
)


def to_dash_case(s: str) -> str:
    return _TO_DASH_CASE_RE.sub('-', s).lower()


class Placeholders(enum.Enum):
    DISABLED = '<disabled>'
    MISSING = '<missing>'

    def __repr__(self):
        return self.value


Disabled = _t.Literal[Placeholders.DISABLED]
DISABLED: Disabled = Placeholders.DISABLED

Missing = _t.Literal[Placeholders.MISSING]
MISSING: Missing = Placeholders.MISSING
