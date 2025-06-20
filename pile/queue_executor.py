from asyncio import AbstractEventLoop, AbstractEventLoopPolicy, CancelledError, SelectorEventLoop, events, futures
import asyncio
import concurrent.futures
import queue
import threading
from typing import Coroutine


class ExecQueueTask(asyncio.Future):
    coro: Coroutine
    def __init__(self, coro: Coroutine):
        self.coro = coro

class ExecQueueFutureFactory:
    exec_queue = queue.Queue()
    stopping: bool = False
    cancelling: bool = False
    exec_count = 0
    exception_count = 0
    last_error: str | None = None
    queue_full_count = 0

    def submit(self, coro: Coroutine, /, *args, **kwargs) -> asyncio.Future:
        task = ExecQueueTask(coro)
        self.exec_queue.put_nowait(task)
        return task

    def shutdown(self, wait=True, *, cancel_futures=False):
        self.stopping = True
        if cancel_futures:
            self.cancelling = True
    
    def pump_busy_loop(self):
        while self.pump_single():
            pass
    
    def _queue_put(self, t: ExecQueueTask):
        try:
            self.exec_queue.put_nowait(t)
        except:
            # task is dropped because queue is full
            self.queue_full_count += 1

    def pump_single(self):
        """Execute some scheduled work. Returns False when pumping should cease"""
        if self.cancelling:
            return False
        task: ExecQueueTask | None = None
        try:
            task = self.exec_queue.get_nowait()
        except queue.Empty as e:
            if self.stopping:
                return False
            return True
        if isinstance(task, ExecQueueTask):
            try:
                if task.cancelled():
                    result = task.coro.throw(CancelledError())
                else:
                    result = task.coro.send(None)
            except StopIteration as exc:
                task.set_result(exc.value)
            except CancelledError as e:
                task.cancel()
            except (KeyboardInterrupt, SystemExit) as exc:
                task.set_exception(exc)
                raise
            except BaseException as exc:
                task.set_exception(exc)
            else:
                blocking = getattr(result, '_asyncio_future_blocking', None)
                if blocking:
                    if result is task:
                        e = RuntimeError(f'Task awaiting itself: {task!r}')
                        task.set_exception(e)
                    else:
                        # it's blocked on something but i'm just going to stick it back in the queue and hope that works.
                        self._queue_put(task)

                else:
                    if result is None:
                        # task is relinquishing control, add it at the back of the queue
                        self._queue_put(task)
                
            # except:
            #     import traceback
            #     tb = traceback.format_exc()
            #     self.last_error = tb
            #     self.exception_count += 1

            self.exec_count += 1
        return True

class QueueExecutor(concurrent.futures.Executor):
    exec_queue = queue.Queue()
    stopping: bool = False
    cancelling: bool = False
    exec_count = 0
    exception_count = 0
    last_error: str | None = None
    loop: AbstractEventLoop | None

    def __init__(self):
        super().__init__()
        self.loop = None

    async def exec_on_queue(self, loop: AbstractEventLoop, coro: Coroutine):
        if not self.loop:
            self.loop = loop

        def iterate():
            try:
                result = coro.send(None)
            except StopIteration as exc:
                return {'status': 'done', 'value': exc.value}
            except CancelledError as e:
                # return coro_throw(CancelledError())
                return {'status': 'cancelled', 'exception': e}
            except (KeyboardInterrupt, SystemExit) as exc:
                # await coro_throw(exc)
                return {'status': 'raised', 'exception': exc}
            except BaseException as exc:
                # await coro_throw(exc)
                return {'status': 'raised', 'exception': exc}
            else:
                blocking = getattr(result, '_asyncio_future_blocking', None)
                if blocking:
                    # wait for whatever
                    # await blocking
                    return {'status': 'blocking', 'on': blocking}
                else:
                    if result is None:
                        return {'status': 'yielding'}

        while True:
            iter_result = await loop.run_in_executor(self, iterate)
            print(iter_result)

    def submit(self, fn, /, *args, **kwargs):
        future = concurrent.futures.Future()
        """Submits a callable to be executed with the given arguments.

        Schedules the callable to be executed as fn(*args, **kwargs) and returns
        a Future instance representing the execution of the callable.

        Returns:
            A Future representing the given call.
        """
        def job():
            if not future.set_running_or_notify_cancel():
                return
            try:
                ret = fn(*args, **kwargs)
                future.set_result(ret)
            except Exception as e:
                future.set_exception(e)
        
        self.exec_queue.put_nowait(job)
        return future

    def shutdown(self, wait=True, *, cancel_futures=False):
        self.stopping = True
        if cancel_futures:
            self.cancelling = True
    
    def pump_busy_loop(self):
        while self.pump_single():
            pass

    def pump_single(self):

        try:
            events.get_event_loop()
        except RuntimeError:
            # make sure the event loop is set on the thread we are pumping from
            events.set_event_loop(self.loop)

        """Execute some scheduled work. Returns False when pumping should cease"""
        if self.cancelling:
            return False
        f = None
        try:
            f = self.exec_queue.get_nowait()
        except queue.Empty as e:
            if self.stopping:
                return False
            return True
        if f:
            try:
                f()
            except:
                import traceback
                tb = traceback.format_exc()
                self.last_error = tb
                self.exception_count += 1

            self.exec_count += 1
        return True

class YieldingEventLoop(asyncio.SelectorEventLoop):
    def _run_once(self):
        def step():
            super().__run_once()


# class CustomEventLoop(AbstractEventLoop):
#     def run_forever(self):
#         """Run the event loop until stop() is called."""
#         raise NotImplementedError

#     def run_until_complete(self, future):
#         """Run the event loop until a Future is done.

#         Return the Future's result, or raise its exception.
#         """
#         raise NotImplementedError

#     def stop(self):
#         """Stop the event loop as soon as reasonable.

#         Exactly how soon that is may depend on the implementation, but
#         no more I/O callbacks should be scheduled.
#         """
#         raise NotImplementedError

#     def is_running(self):
#         """Return whether the event loop is currently running."""
#         raise NotImplementedError

#     def is_closed(self):
#         """Returns True if the event loop was closed."""
#         raise NotImplementedError

#     def close(self):
#         """Close the loop.

#         The loop should not be running.

#         This is idempotent and irreversible.

#         No other methods should be called after this one.
#         """
#         raise NotImplementedError

#     async def shutdown_asyncgens(self):
#         """Shutdown all active asynchronous generators."""
#         raise NotImplementedError

#     async def shutdown_default_executor(self):
#         """Schedule the shutdown of the default executor."""
#         raise NotImplementedError

#     # Methods scheduling callbacks.  All these return Handles.

#     def _timer_handle_cancelled(self, handle):
#         """Notification that a TimerHandle has been cancelled."""
#         raise NotImplementedError

#     def call_soon(self, callback, *args, context=None):
#         return self.call_later(0, callback, *args, context=context)

#     def call_later(self, delay, callback, *args, context=None):
#         raise NotImplementedError

#     def call_at(self, when, callback, *args, context=None):
#         raise NotImplementedError

#     def time(self):
#         raise NotImplementedError

#     def create_future(self):
#         raise NotImplementedError

#     # Method scheduling a coroutine object: create a task.

#     def create_task(self, coro, *, name=None, context=None):
#         raise NotImplementedError

#     # Methods for interacting with threads.

#     def call_soon_threadsafe(self, callback, *args, context=None):
#         raise NotImplementedError

#     def run_in_executor(self, executor, func, *args):
#         raise NotImplementedError

#     def set_default_executor(self, executor):
#         raise NotImplementedError

#     # Network I/O methods returning Futures.

#     async def getaddrinfo(self, host, port, *,
#                           family=0, type=0, proto=0, flags=0):
#         raise NotImplementedError

#     async def getnameinfo(self, sockaddr, flags=0):
#         raise NotImplementedError

#     async def create_connection(
#             self, protocol_factory, host=None, port=None,
#             *, ssl=None, family=0, proto=0,
#             flags=0, sock=None, local_addr=None,
#             server_hostname=None,
#             ssl_handshake_timeout=None,
#             ssl_shutdown_timeout=None,
#             happy_eyeballs_delay=None, interleave=None):
#         raise NotImplementedError

#     async def create_server(
#             self, protocol_factory, host=None, port=None,
#             *, family=socket.AF_UNSPEC,
#             flags=socket.AI_PASSIVE, sock=None, backlog=100,
#             ssl=None, reuse_address=None, reuse_port=None,
#             ssl_handshake_timeout=None,
#             ssl_shutdown_timeout=None,
#             start_serving=True):
#         """A coroutine which creates a TCP server bound to host and port.

#         The return value is a Server object which can be used to stop
#         the service.

#         If host is an empty string or None all interfaces are assumed
#         and a list of multiple sockets will be returned (most likely
#         one for IPv4 and another one for IPv6). The host parameter can also be
#         a sequence (e.g. list) of hosts to bind to.

#         family can be set to either AF_INET or AF_INET6 to force the
#         socket to use IPv4 or IPv6. If not set it will be determined
#         from host (defaults to AF_UNSPEC).

#         flags is a bitmask for getaddrinfo().

#         sock can optionally be specified in order to use a preexisting
#         socket object.

#         backlog is the maximum number of queued connections passed to
#         listen() (defaults to 100).

#         ssl can be set to an SSLContext to enable SSL over the
#         accepted connections.

#         reuse_address tells the kernel to reuse a local socket in
#         TIME_WAIT state, without waiting for its natural timeout to
#         expire. If not specified will automatically be set to True on
#         UNIX.

#         reuse_port tells the kernel to allow this endpoint to be bound to
#         the same port as other existing endpoints are bound to, so long as
#         they all set this flag when being created. This option is not
#         supported on Windows.

#         ssl_handshake_timeout is the time in seconds that an SSL server
#         will wait for completion of the SSL handshake before aborting the
#         connection. Default is 60s.

#         ssl_shutdown_timeout is the time in seconds that an SSL server
#         will wait for completion of the SSL shutdown procedure
#         before aborting the connection. Default is 30s.

#         start_serving set to True (default) causes the created server
#         to start accepting connections immediately.  When set to False,
#         the user should await Server.start_serving() or Server.serve_forever()
#         to make the server to start accepting connections.
#         """
#         raise NotImplementedError

#     async def sendfile(self, transport, file, offset=0, count=None,
#                        *, fallback=True):
#         """Send a file through a transport.

#         Return an amount of sent bytes.
#         """
#         raise NotImplementedError

#     async def start_tls(self, transport, protocol, sslcontext, *,
#                         server_side=False,
#                         server_hostname=None,
#                         ssl_handshake_timeout=None,
#                         ssl_shutdown_timeout=None):
#         """Upgrade a transport to TLS.

#         Return a new transport that *protocol* should start using
#         immediately.
#         """
#         raise NotImplementedError

#     async def create_unix_connection(
#             self, protocol_factory, path=None, *,
#             ssl=None, sock=None,
#             server_hostname=None,
#             ssl_handshake_timeout=None,
#             ssl_shutdown_timeout=None):
#         raise NotImplementedError

#     async def create_unix_server(
#             self, protocol_factory, path=None, *,
#             sock=None, backlog=100, ssl=None,
#             ssl_handshake_timeout=None,
#             ssl_shutdown_timeout=None,
#             start_serving=True):
#         """A coroutine which creates a UNIX Domain Socket server.

#         The return value is a Server object, which can be used to stop
#         the service.

#         path is a str, representing a file system path to bind the
#         server socket to.

#         sock can optionally be specified in order to use a preexisting
#         socket object.

#         backlog is the maximum number of queued connections passed to
#         listen() (defaults to 100).

#         ssl can be set to an SSLContext to enable SSL over the
#         accepted connections.

#         ssl_handshake_timeout is the time in seconds that an SSL server
#         will wait for the SSL handshake to complete (defaults to 60s).

#         ssl_shutdown_timeout is the time in seconds that an SSL server
#         will wait for the SSL shutdown to finish (defaults to 30s).

#         start_serving set to True (default) causes the created server
#         to start accepting connections immediately.  When set to False,
#         the user should await Server.start_serving() or Server.serve_forever()
#         to make the server to start accepting connections.
#         """
#         raise NotImplementedError

#     async def connect_accepted_socket(
#             self, protocol_factory, sock,
#             *, ssl=None,
#             ssl_handshake_timeout=None,
#             ssl_shutdown_timeout=None):
#         """Handle an accepted connection.

#         This is used by servers that accept connections outside of
#         asyncio, but use asyncio to handle connections.

#         This method is a coroutine.  When completed, the coroutine
#         returns a (transport, protocol) pair.
#         """
#         raise NotImplementedError

#     async def create_datagram_endpoint(self, protocol_factory,
#                                        local_addr=None, remote_addr=None, *,
#                                        family=0, proto=0, flags=0,
#                                        reuse_address=None, reuse_port=None,
#                                        allow_broadcast=None, sock=None):
#         """A coroutine which creates a datagram endpoint.

#         This method will try to establish the endpoint in the background.
#         When successful, the coroutine returns a (transport, protocol) pair.

#         protocol_factory must be a callable returning a protocol instance.

#         socket family AF_INET, socket.AF_INET6 or socket.AF_UNIX depending on
#         host (or family if specified), socket type SOCK_DGRAM.

#         reuse_address tells the kernel to reuse a local socket in
#         TIME_WAIT state, without waiting for its natural timeout to
#         expire. If not specified it will automatically be set to True on
#         UNIX.

#         reuse_port tells the kernel to allow this endpoint to be bound to
#         the same port as other existing endpoints are bound to, so long as
#         they all set this flag when being created. This option is not
#         supported on Windows and some UNIX's. If the
#         :py:data:`~socket.SO_REUSEPORT` constant is not defined then this
#         capability is unsupported.

#         allow_broadcast tells the kernel to allow this endpoint to send
#         messages to the broadcast address.

#         sock can optionally be specified in order to use a preexisting
#         socket object.
#         """
#         raise NotImplementedError

#     # Pipes and subprocesses.

#     async def connect_read_pipe(self, protocol_factory, pipe):
#         """Register read pipe in event loop. Set the pipe to non-blocking mode.

#         protocol_factory should instantiate object with Protocol interface.
#         pipe is a file-like object.
#         Return pair (transport, protocol), where transport supports the
#         ReadTransport interface."""
#         # The reason to accept file-like object instead of just file descriptor
#         # is: we need to own pipe and close it at transport finishing
#         # Can got complicated errors if pass f.fileno(),
#         # close fd in pipe transport then close f and vice versa.
#         raise NotImplementedError

#     async def connect_write_pipe(self, protocol_factory, pipe):
#         """Register write pipe in event loop.

#         protocol_factory should instantiate object with BaseProtocol interface.
#         Pipe is file-like object already switched to nonblocking.
#         Return pair (transport, protocol), where transport support
#         WriteTransport interface."""
#         # The reason to accept file-like object instead of just file descriptor
#         # is: we need to own pipe and close it at transport finishing
#         # Can got complicated errors if pass f.fileno(),
#         # close fd in pipe transport then close f and vice versa.
#         raise NotImplementedError

#     async def subprocess_shell(self, protocol_factory, cmd, *,
#                                stdin=subprocess.PIPE,
#                                stdout=subprocess.PIPE,
#                                stderr=subprocess.PIPE,
#                                **kwargs):
#         raise NotImplementedError

#     async def subprocess_exec(self, protocol_factory, *args,
#                               stdin=subprocess.PIPE,
#                               stdout=subprocess.PIPE,
#                               stderr=subprocess.PIPE,
#                               **kwargs):
#         raise NotImplementedError

#     # Ready-based callback registration methods.
#     # The add_*() methods return None.
#     # The remove_*() methods return True if something was removed,
#     # False if there was nothing to delete.

#     def add_reader(self, fd, callback, *args):
#         raise NotImplementedError

#     def remove_reader(self, fd):
#         raise NotImplementedError

#     def add_writer(self, fd, callback, *args):
#         raise NotImplementedError

#     def remove_writer(self, fd):
#         raise NotImplementedError

#     # Completion based I/O methods returning Futures.

#     async def sock_recv(self, sock, nbytes):
#         raise NotImplementedError

#     async def sock_recv_into(self, sock, buf):
#         raise NotImplementedError

#     async def sock_recvfrom(self, sock, bufsize):
#         raise NotImplementedError

#     async def sock_recvfrom_into(self, sock, buf, nbytes=0):
#         raise NotImplementedError

#     async def sock_sendall(self, sock, data):
#         raise NotImplementedError

#     async def sock_sendto(self, sock, data, address):
#         raise NotImplementedError

#     async def sock_connect(self, sock, address):
#         raise NotImplementedError

#     async def sock_accept(self, sock):
#         raise NotImplementedError

#     async def sock_sendfile(self, sock, file, offset=0, count=None,
#                             *, fallback=None):
#         raise NotImplementedError

#     # Signal handling.

#     def add_signal_handler(self, sig, callback, *args):
#         raise NotImplementedError

#     def remove_signal_handler(self, sig):
#         raise NotImplementedError

#     # Task factory.

#     def set_task_factory(self, factory):
#         raise NotImplementedError

#     def get_task_factory(self):
#         raise NotImplementedError

#     # Error handlers.

#     def get_exception_handler(self):
#         raise NotImplementedError

#     def set_exception_handler(self, handler):
#         raise NotImplementedError

#     def default_exception_handler(self, context):
#         raise NotImplementedError

#     def call_exception_handler(self, context):
#         raise NotImplementedError

#     # Debug flag management.

#     def get_debug(self):
#         raise NotImplementedError

#     def set_debug(self, enabled):
#         raise NotImplementedError

# class CustomEventLoopPolicy(AbstractEventLoopPolicy):
#     _loop: CustomEventLoop | None
#     def new_event_loop(self) -> AbstractEventLoop:
#         if self._loop:
#             # this is not really correct, it should create a new one
#             return self._loop
#         self._loop = CustomEventLoop()
#         return self._loop
#     def get_event_loop(self) -> AbstractEventLoop:
#         return self.new_event_loop()
#     def set_event_loop(self, loop: AbstractEventLoop | None) -> None:
#         self._loop = loop # type: ignore