from interactive.picker.items import PickableBase, PickedAction, PickedResult
from sink.errors import stub

class ItemPickerBase:
    """Base for item pickers"""
    def __init__(self, title: str, items: list[PickableBase]):
        self.title = title
        self.items = items
    def run(self) -> PickedResult:
        while True:
            result = self._present_items()
            if result.action == PickedAction.PICK_AGAIN:
                continue
            elif result.action == PickedAction.PICK_PARENT:
                this_result = PickedResult(action=PickedAction.PICK_AGAIN, message=result.message)
                return this_result
            elif result.action == PickedAction.EXIT:
                return result
            else:
                raise Exception(f'Action variant not handled: {result.action} in result {result} for picker {self.title}')

    def _present_items(self) -> PickedResult:
        stub()
        raise Exception() # will throw inside of stub, this is just here to satisfy static analysis
