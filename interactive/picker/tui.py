
from interactive.picker import ItemPickerBase, PickableBase

class TuiItemPicker(ItemPickerBase):
    """A mixed graphical & tui item picker"""
    def __init__(self, title: str, items: list[PickableBase]):
        super().__init__(title, items)
        self.title = title
        self.items = items
    def run(self):
        self.run_tui()

    def run_tui(self):
        from pick import pick
        options = [x.label for x in self.items]
        selected, idx = pick(options, self.title, multiselect=False, min_selection_count=1)
        print(selected)
        item = self.items[idx] # type: ignore
        item.picked()