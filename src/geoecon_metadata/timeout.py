import multiprocessing
import concurrent.futures
import threading
import signal


class TimeoutException(Exception):
    def __init__(self, typo, message, seconds):
        self.typo = typo
        self.message = message
        self.time = seconds

    def __str__(self):
        return f"TimeoutException:{self.typo}:{self.message}:{self.time}s"


def timeout_threads(seconds):
    def decorator(func):
        def wrapper(*args, **kwargs):
            result = [
                TimeoutException(
                    "error",
                    f"Process {func.__name__} takes to much time.",
                    seconds,
                )
            ]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    result[0] = e

            thread = threading.Thread(target=target)
            thread.start()
            thread.join(seconds)
            if thread.is_alive():
                raise TimeoutException(
                    "error",
                    f"Process {func.__name__} takes to much time.",
                    seconds,
                )
            else:
                if isinstance(result[0], Exception):
                    raise result[0]
                return result[0]

        return wrapper

    return decorator

def timeout_sign(seconds):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutException("error", f"Function {func.__name__} took too long to complete.")

        def wrapper(*args, **kwargs):
            # Set the signal handler and a timeout limit
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)  # Start the timer

            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)  # Disable the alarm

            return result

        return wrapper
    return decorator

def timeout_null(seconds):
    def decorator(func):
        return func
    return decorator

try:
    signal.SIGALRM
    timeout = timeout_sign 
except:
    timeout = timeout_threads

timeout = timeout_null
