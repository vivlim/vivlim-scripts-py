from typing import Iterable
from interactive.picker.items import PickableBase, PickedAction, PickedResult
from interactive.picker.pickers import ItemPickerBase
from interactive.picker.pickers.tui import TuiItemPicker
from sink.errors import stub
from enum import Enum

class AutoItemPicker(ItemPickerBase):
    """A mixed graphical & tui item picker"""
    def __init__(self, title: str, items: list[PickableBase]):
        super().__init__(title, items)

        # currently only wraps tui
        self.inner = TuiItemPicker(title, items)
        
    def run(self) -> PickedResult:
        return self.inner.run()
    
    def _present_items(self) -> PickedResult:
        raise Exception('_present_items on AutoItemPicker shouldn\'t be called, it should delegate to an inner picker instead')