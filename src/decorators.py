import time


def measure_time(func):
    """
    A decorator that measures the execution time of a function.

    Args:
        func (callable): The function whose execution time is to be measured.

    Returns:
        callable: A wrapper function that measures and returns the execution time and result of the original function.

    Example:
        @measure_time
        def example_function(n):
            time.sleep(n)
            return f"Slept for {n} seconds"

        elapsed_time, result = example_function(2)
        print(f"Elapsed time: {elapsed_time} seconds")
        print(f"Result: {result}")
    """

    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return end_time - start_time, result

    return wrapper
