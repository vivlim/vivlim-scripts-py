import unittest, logging, sys

class _BufferingHandler(logging.Handler):
    def __init__(self, *args):
        super().__init__(*args)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class LoggedTestCase(unittest.TestCase):
    """Test case which accumulates logs as it runs and only prints them if there is a failure or error"""
    def __init__(self, *args):
        super().__init__(*args)

        self.logger = logging.getLogger("bufferingLogger")
        self.logger.setLevel(logging.DEBUG)

    def setUp(self):
        super().setUp()
        for hdlr in self.logger.handlers:
           self.logger.removeHandler(hdlr)
        self.logbuf = _BufferingHandler()
        self.logger.addHandler(self.logbuf)

    def tearDown(self):
        super().tearDown()
        self.logger.removeHandler(self.logbuf)

    def run(self, result=None):
        super().run(result)
        if result and (len(result.failures) + len(result.errors)) > 0:
            sh = logging.StreamHandler(sys.stdout)
            for r in self.logbuf.records:
                sh.emit(r)