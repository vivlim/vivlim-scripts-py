import unittest, logging, asyncio

from queue_executor import ExecQueueFutureFactory, QueueExecutor
from sink.unittest import LoggedTestCase

class TestQueueExecutor(LoggedTestCase):
    def test_basic_coroutine(self):
        qe = QueueExecutor()
        # qe = ExecQueueFutureFactory()

        items = []
        async def push(s, wait=0):
            await asyncio.sleep(wait)
            items.append(s)
        
        def ex_handler(loop, context):
            self.logger.error(f'exception in loop')

        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # loop.set_exception_handler(ex_handler)
        # loop.set_default_executor(qe)

        

        import threading
        def pump_thread():
            qe.pump_busy_loop()
        
        t =threading.Thread(target=pump_thread)
        t.start()

        async def run_test_on_executor():
            loop = asyncio.get_running_loop()

            async def test():
                self.logger.info('test: pushing a')
                await push('a', 0)
                self.logger.info('test: pushing b')
                await push('b', 2)
                self.logger.info('test: pushing c')
                await push('c', 1)
                self.logger.info('test: done')
                # request shutdown now.

            await qe.exec_on_queue(loop, test())
            qe.shutdown(wait=False, cancel_futures=False)
            # await test()

        self.logger.info('main: begin run_until_complete')
        # loop.run_in_executor(qe, test)
        asyncio.run(run_test_on_executor())
        self.logger.info('main: end run_until_complete')
        # qe.pump_busy_loop()
        # qe.shutdown(wait=False, cancel_futures=True)
        t.join()
        self.logger.info('main: joined pump thread')
        self.assertGreater(qe.exec_count, 0)
        self.assertListEqual(items, ['a', 'b', 'c'])


if __name__ == '__main__':
    unittest.main()