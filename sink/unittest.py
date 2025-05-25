import unittest, logging, sys
# https://stackoverflow.com/a/15969985

class LogThisTestCase(type):
    def __new__(cls, name, bases, dct):
        # if the TestCase already provides setUp, wrap it
        if 'setUp' in dct:
            setUp = dct['setUp']
        else:
            setUp = lambda self: None

        def wrappedSetUp(self):
            # for hdlr in self.logger.handlers:
            #    self.logger.removeHandler(hdlr)
            self.hdlr = logging.StreamHandler(sys.stdout)
            self.logger.addHandler(self.hdlr)
            setUp(self)
        dct['setUp'] = wrappedSetUp

        # same for tearDown
        if 'tearDown' in dct:
            tearDown = dct['tearDown']
        else:
            tearDown = lambda self: None

        def wrappedTearDown(self):
            tearDown(self)
            self.logger.removeHandler(self.hdlr)

        def wrappedRun(self, result=None):
            print("wrapped run")
            self.logger.error("runnn")
            self.run(result)

        dct['tearDown'] = wrappedTearDown
        dct['run'] = wrappedRun

        # return the class instance with the replaced setUp/tearDown
        return type.__new__(cls, name, bases, dct)

class LoggedTestCase(unittest.TestCase):
    def __init__(self, *args):
        super().__init__(*args)

        self.logger = logging.getLogger("unittestLogger")
        self.logger.setLevel(logging.DEBUG) # or whatever you prefer

    def setUp(self):
        super().setUp()
        # for hdlr in self.logger.handlers:
        #    self.logger.removeHandler(hdlr)
        self.hdlr = logging.StreamHandler(sys.stdout)
        self.logger.addHandler(self.hdlr)

    def tearDown(self):
        super().tearDown()
        self.logger.removeHandler(self.hdlr)

    def wrappedRun(self, result=None):
        print("wrapped run")
        self.logger.error("runnn")
        self.run(result)