from interactive.picker.items import PickableBase, PickedResult
from interactive.picker.pickers import ItemPickerBase


class NestedPickerPickable(PickableBase):
    def __init__(self, label: str, inner_picker: ItemPickerBase):
        super().__init__(label)
        self.inner_picker = inner_picker
    
    def picked(self) -> PickedResult:
        result = self.inner_picker.run()
        return result