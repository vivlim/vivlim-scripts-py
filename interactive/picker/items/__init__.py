
from enum import Enum


class PickedAction(Enum):
    PICK_AGAIN = 1
    PICK_PARENT = 2
    EXIT = 3

class PickedResult:
    def __init__(self, action: PickedAction, message: str | None = None):
        self.action = action
        self.message = message

class PickableBase:
    def __init__(self, label: str):
        self.label = label
    def picked(self) -> PickedResult:
        return PickedResult(PickedAction.PICK_AGAIN, f'Not implemented: {self.label}')
    def enabled(self) -> bool:
        return True
    def __str__(self) -> str:
        return f'{self.label} ({self.weight()})'
    def weight(self):
        """Higher numbers are more likely to be picked. Default is 1 with the label turned into a fractional component for ordering"""
        import string
        w = 1.0
        current_factor = 1
        step = 0.1

        for c in self.label.lower():
            current_factor = current_factor * step
            letter_idx = string.ascii_lowercase.find(c)
            if letter_idx >= 0:
                ratio = 1 - (float(letter_idx) / len(string.ascii_lowercase)) # 1- to reverse it, since larger values are higher weighted
                # letter indices are assigned a number line position between [1,5]
                assignment = (4 * ratio) + 1
                w = w + (assignment * current_factor)
                continue
            
            # maybe it is a number?
            try:
                int_value = int(c)
                ratio = 1 - (float(int_value) / 10)
                # number indices are assigned somewhere between [6,8] so they take precedence over letters
                assignment = (2 * ratio) + 6
                w = w + (assignment * current_factor)
                continue

            except (TypeError, ValueError):
                # characters that aren't letters or numbers will not contribute to weight
                continue

        return w
