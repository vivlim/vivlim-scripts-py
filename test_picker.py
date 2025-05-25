#!/usr/bin/env -S uv run 

from interactive.picker.items import PickableBase
from interactive.picker.pickers.auto import AutoItemPicker
from interactive.picker.builders import build_tree

def main() -> None:
    p = build_tree('test picker', AutoItemPicker, [
        PickableBase("hello"),
        PickableBase("world"),
        ('nested', [
            PickableBase("inner item 1"),
            PickableBase("inner item 2")
        ])
    ])
    p.run()


if __name__ == "__main__":
    main()
