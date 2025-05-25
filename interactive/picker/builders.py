
from typing import Iterable
from interactive.picker.items import PickableBase, PickedAction, PickedResult
from interactive.picker.pickers import ItemPickerBase
from sink.errors import stub
from collections import namedtuple
from enum import Enum


type PickableTree = PickableBase | tuple[str, Iterable[PickableTree]]

def build_tree(title: str, picker: type[ItemPickerBase], pickables: list[PickableTree]):
    from interactive.picker.items.nested_picker import NestedPickerPickable
    def build_tree_rec(pt: PickableTree) -> PickableBase:
        if isinstance(pt, tuple):
            # create the picker that this will open when picked
            items = [build_tree_rec(x) for x in pt[1]]
            inner_picker = picker(title=pt[0], items=items)
            # now create the pickable that will use it
            p = NestedPickerPickable(pt[0], inner_picker)
            return p
        else:
            # It's already a pickable
            return pt

    root_items = [build_tree_rec(x) for x in pickables]
    root = picker(title, root_items)
    return root