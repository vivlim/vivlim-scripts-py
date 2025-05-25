import unittest, logging
from random import shuffle

from interactive.picker.items import PickableBase
from sink.unittest import LoggedTestCase

class TestPickableItems(LoggedTestCase):
    def test_item_label_ordering(self):
        names = [
            "hello world",
            "hello whirled",
            "hello whorled",
            "hi world",
            "ha world",
            "h1 world",
            "h9 world",
        ]
        shuffle(names)
        sorted_names = sorted(names)

        items = [PickableBase(n) for n in names]

        def get_pickable_weight(p: PickableBase):
            return p.weight()

        items_sorted_by_weight = sorted(items, key=get_pickable_weight, reverse=True)
        self.logger.error("blahh")

        self.logger.info(f'sorted pickables:')
        for i in items_sorted_by_weight:
            self.logger.info(f'- {str(i)}')

        for pickable, name in zip(items_sorted_by_weight, sorted_names):
            self.assertEqual(pickable.label, name)


if __name__ == '__main__':
    unittest.main()