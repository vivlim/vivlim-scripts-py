class NotImplementedError(Exception):
    """Error for methods that haven't been implemented."""
def stub():
    import inspect
    frame = inspect.currentframe()
    if not frame:
        raise NotImplementedError("Method not implemented, current frame unknown")
    caller_frame = frame.f_back
    if not caller_frame:
        raise NotImplementedError("Method not implemented, caller frame unknown")
    caller = caller_frame.f_code
    raise NotImplementedError(f"Method not implemented: {caller.co_name} (in {caller.co_filename}:{caller.co_firstlineno})")