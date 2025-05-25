
from time import sleep
from interactive.picker.items import PickedAction, PickedResult
from interactive.picker.pickers import ItemPickerBase

class TuiItemPicker(ItemPickerBase):
    from interactive.picker.items import PickableBase, PickedResult
    """A tui item picker"""
    def __init__(self, title: str, items: list[PickableBase]):
        super().__init__(title, items)
        self.base_title = title
        self.title = title
        self.items = items
        self.default_index = 0

    def _present_items(self) -> PickedResult:
        return self.run_tui()

    def run_tui(self) -> PickedResult:
        from pick import pick
        options = [x.label for x in self.items]
        selected, idx = pick(options, self.title, multiselect=False, min_selection_count=1, default_index=self.default_index, quit_keys=[ord('q'), 27])

        if not selected:
            return PickedResult(action=PickedAction.PICK_PARENT, message='exited')

        # print(f'sel: {selected}, idx: {idx}')
        # sleep(3)
        item = self.items[idx] # type: ignore
        result = item.picked()

        # if this picker is shown again, update its state with some info
        self.title = f"{self.base_title} | {item.label} -> {result.message}"
        self.default_index = idx
        return result