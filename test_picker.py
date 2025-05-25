#!/usr/bin/env -S uv run 

from interactive.picker import *

def main() -> None:
    items = [
        PickableBase("hello"),
        PickableBase("world"),
    ]
    p = ItemPickerBase("test", items)
    p.run()


if __name__ == "__main__":
    main()
