import time
import unittest, logging, asyncio

from queue_executor import ExecQueueFutureFactory, QueueExecutor
from sink.unittest import LoggedTestCase

class TestAsync(LoggedTestCase):
    def test_async_yielder(self):
        def yield_execution() -> asyncio.Future:
            loop = asyncio.get_running_loop()
            fut = loop.create_future()
            def resumer():
                time.sleep(1)
                fut.set_result(None)
                
            import threading
            t = threading.Thread(target=resumer)
            t.start()
            return fut

        async def run_test_async():
            self.logger.info("before")
            await yield_execution()
            self.logger.info("after")

        self.logger.info('main: begin run_until_complete')
        # loop.run_in_executor(qe, test)
        asyncio.run(run_test_async())
        self.logger.info('main: end run_until_complete')


if __name__ == '__main__':
    unittest.main()