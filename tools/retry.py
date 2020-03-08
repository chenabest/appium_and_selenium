# achen 2019/11/19
from config import SENTRY
from functools import wraps
from selenium.common.exceptions import NoSuchElementException
import time


class Retry:
    def __init__(self, timeout=5, poll_frequency=0.25, retry_exponential_base=2, prompt=True, raise_exception=True):
        """
        自动重试，作为装饰器使用
        :param timeout: 超时时间，超过后将不再重试。
        :param poll_frequency: 决定重试的频率
        :param retry_exponential_base: 重试后的等待时间等于=poll_frequency*exponential_base**retry_times
        :param prompt: 重试提示信息，值为False时，不显示提示信息。
        :param raise_exception: 值为False时，不抛出异常
        """
        self._timeout = timeout
        self._poll = poll_frequency
        self._base = retry_exponential_base
        self._prompt = prompt
        self._raise_exception = raise_exception

    def retry_until_done_or_timeout(self, find_element_method):
        @wraps(find_element_method)
        def wrapper(*args, **kwargs):
            timeout = kwargs.get('timeout', self._timeout)
            poll_frequency = kwargs.get('poll_frequency', self._poll)
            exponential_base = kwargs.get('retry_exponential_base', self._base)
            raise_exception = kwargs.get('raise_exception', self._raise_exception)
            prompt = kwargs.get('prompt', self._prompt)
            end_time = time.time() + timeout
            retry_times = 0
            # print('timeout={}, poll_frequcency={}, exponential_base={}, prompt={}, raise_exception={}'.
            #       format(timeout, poll_frequency, exponential_base, prompt, raise_exception))
            while True:
                try:
                    return find_element_method(*args, **kwargs)
                except NoSuchElementException as e:
                    screen = getattr(e, 'screen', None)
                    stacktrace = getattr(e, 'stacktrace', None)
                    if time.time() > end_time:
                        break
                    if prompt:
                        print('fail to locate element: %s, retry...' % args[1])
                time.sleep(poll_frequency*exponential_base**retry_times)
                retry_times += 1
            if 'position_dict' in kwargs:
                kwargs.pop('position_dict')
            if 'xpath_list' in kwargs:
                kwargs.pop('xpath_list')
            message = 'retry failed, element information: ' + str(args)[1: -1] + (', ' + str(kwargs) if kwargs else '')
            if prompt:
                print(message)
            if raise_exception:
                raise NoSuchElementException(message, screen, stacktrace)
        return wrapper
