from selenium.common.exceptions import NoSuchElementException
import time
from selenium.webdriver.common.by import By
import sys
from appium_robot.robot.tools.retry import Retry
from functools import wraps
from traceback import print_exc
import os

"""
关于参数配置
下面配置的参数主要是Retry对象RETRY，决定等待时间规则的一些参数和EXPECT_ELEMENT。
这些参数作为全局变量，均有默认值，支持每个脚本内统一配置，支持在调用方法时传参，覆盖统一配置的值。
"""

PROJECT_NAME = 'data_automation'
RETRY = Retry()
IS_ELEMENT_PRESENT_TIMEOUT = 1
BACK_WAIT_TIME = 1
SWIPE_WAIT_TIME = 1.5
MAX_RETRIES = 4
CLICK_WAIT_TIME = 0.25
EXPONENTIAL_BASE = 1
EXPECT_ELEMENT = 'page_source'
"""
从主模块（执行的脚本文件）中导入相关配置：RETRY，MAX_RETRIES，CLICK_WAIT_TIME，EXPONENTIAL_BASE, IS_ELEMENT_PRESENT_TIMEOUT，EXPECT_ELEMENT
"""
try:
    filepath = sys.argv[0]
    ls = filepath.split(r'/')
    for i in range(len(ls)):
        if ls[i] == PROJECT_NAME:
            break
    path_position = '.'.join(ls[i+1:])[:-3]
except Exception as e:
    print(e)
    print_exc()
    path_position = ''
if path_position:
    print(path_position, '导入相关参数配置')
    for g in ['RETRY', 'MAX_RETRIES', 'CLICK_WAIT_TIME', 'EXPONENTIAL_BASE',
              'IS_ELEMENT_PRESENT_TIMEOUT', 'SWIPE_WAIT_TIME', 'BACK_WAIT_TIME', 'EXPECT_ELEMENT']:
        try:
            exec("from %s import %s" % (path_position, g))
        except ImportError:
            pass
print('RETRY配置如下：')
print("timeout=%s, poll_frequency=%s, retry_exponential_base=%s, prompt=%s, raise_exception=%s" % (
    RETRY._timeout, RETRY._poll, RETRY._base, RETRY._prompt, RETRY._raise_exception))
print('MyDriver配置如下：')
print('is_element_present_timeout=%s, swipe_wait_time=%s, back_wait_time=%s' %
      (IS_ELEMENT_PRESENT_TIMEOUT, SWIPE_WAIT_TIME, BACK_WAIT_TIME))
print('MyElement配置如下：')
print('max_retries=%s, click_wait_time=%s, exponential_base=%s' % (
    MAX_RETRIES, CLICK_WAIT_TIME, EXPONENTIAL_BASE))
print('公共配置：')
print('expect_element=%s' % EXPECT_ELEMENT)


def expectation(method, _expect_element=None, _max_retries=0, _wait_time=1, _relation='or', _rtn=1, _raise_exception=True):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        expect_element = kwargs.get('expect_element', _expect_element)
        max_retries = kwargs.get('max_retries', _max_retries)
        wait_time = kwargs.get('wait_time', _wait_time)
        relation = kwargs.get('relation', _relation)
        rtn = kwargs.get('rtn', _rtn)
        raise_exception = kwargs.get('raise_exception', _raise_exception)
        kwargs['raise_exception'] = True
        if isinstance(expect_element, list):
            if relation == 'or':
                for times in range(max_retries+1):
                    method(self, *args, **kwargs)
                    time.sleep(wait_time)
                    flag = False
                    for value in expect_element:
                        try:
                            element = self.find_element_by_adaptor(value, **kwargs)
                            flag = True
                            break
                        except NoSuchElementException:
                            pass
                    if flag:
                        if rtn == 1:
                            return element
                        elif rtn == 0:
                            return self
                        else:
                            raise ValueError('rtn值不对')
                if raise_exception:
                    raise Exception(f'执行方法{method.__name__}后，未找到期望元素列表:%s中的任一元素' % str(expect_element))
            elif relation == 'and':
                for times in range(max_retries+1):
                    # self.driver.swipe(start_x, start_y, end_x, end_y, duration)
                    method(self, *args, **kwargs)
                    time.sleep(wait_time)
                    elements = list()
                    for value in expect_element:
                        try:
                            element = self.find_element_by_adaptor(value, **kwargs)
                            elements.append(element)
                        except NoSuchElementException:
                            elements = list()
                            break
                    if elements:
                        if rtn == 0:
                            return self
                        else:
                            return elements[rtn - 1]
                if raise_exception:
                    raise Exception(f'执行方法{method.__name__}后，未找到期望元素列表:%s中的全部元素' % str(expect_element))
            else:
                raise ValueError('relation值不对')
        elif expect_element == 'page_source':
            page_source = self.page_source
            for times in range(max_retries + 1):
                method(self, *args, **kwargs)
                time.sleep(wait_time)
                if self.page_source != page_source:
                    return self
            if raise_exception:
                raise Exception(f'执行方法{method.__name__}后，页面无变化')
        elif expect_element is not None:
            for times in range(max_retries+1):
                method(self, *args, **kwargs)
                time.sleep(wait_time)
                try:
                    return self.find_element_by_adaptor(expect_element, **kwargs)
                except NoSuchElementException:
                    pass
            if raise_exception:
                raise NoSuchElementException(f'执行方法{method.__name__}后，未找到期望出现的元素:%s' % expect_element)
        else:
            method(self, *args, **kwargs)
            time.sleep(wait_time)
            return self
    return wrapper


class MyDriver(object):
    """
    关于expect_element:
    执行某个动作（滑动，返回，点击等）后，会预期页面出现某个元素，根据期望的元素是否出现，来判断动作是否成功。
    这个需求非常普遍，因此应当作为一个基本功能。
    """
    def __init__(self, web_driver, serial=None, position_dict=None, xpath_list=None):
        self.driver = web_driver
        self.serial = serial
        self.position_dict = position_dict
        self.xpath_list = xpath_list

    @RETRY.retry_until_done_or_timeout
    def find_element_by_xpath(self, xpath, element_name=None, position_dict=None, xpath_list=None, **kwargs):
        if position_dict is None:
            position_dict = self.position_dict
        if xpath_list is None:
            xpath_list = self.xpath_list
        element_name = element_name if element_name else xpath
        element = self.driver.find_element_by_xpath(xpath)
        my_element = MyElement(element, element_name, self)
        if my_element and position_dict is not None and isinstance(position_dict, dict):
            position_dict[xpath] = my_element.get_center_position()
        if xpath_list is not None and isinstance(xpath_list, list):
            xpath_list.append(xpath)
        return my_element

    @RETRY.retry_until_done_or_timeout
    def find_elements_by_xpath(self, xpath, element_name=None, **kwargs):
        element_name = element_name if element_name else xpath
        elements = self.driver.find_elements_by_xpath(xpath)
        return (MyElement(element, element_name, self) for element in elements)

    @RETRY.retry_until_done_or_timeout
    def find_element_by_android_uiautomator(self, value, element_name=None, **kwargs):
        element_name = element_name if element_name else value
        element = self.driver.find_element_by_android_uiautomator(value)
        return MyElement(element, element_name, self)

    def is_element_present_by_xpath(self, xpath, element_name=None,
                                    is_element_present_timeout=IS_ELEMENT_PRESENT_TIMEOUT) -> bool:
        try:
            self.find_element_by_xpath(xpath, element_name, timeout=is_element_present_timeout,
                                       raise_exception=True, prompt=False)
            return True
        except (NoSuchElementException, Exception):
            return False

    def is_element_present_by_android_uiautomator(self, value, element_name=None,
                                                  is_element_present_timeout=IS_ELEMENT_PRESENT_TIMEOUT) -> bool:
        try:
            self.find_element_by_xpath(value, element_name, timeout=is_element_present_timeout,
                                       raise_exception=True, prompt=False)
            return True
        except (NoSuchElementException, Exception):
            return False

    def is_element_present_by_adaptor(self, value, **kwargs):
        if r'//' in value or r'/' in value or '@' in value:
            return self.is_element_present_by_xpath(value, **kwargs)
        elif 'new UiSelector()' in value:
            return self.is_element_present_by_android_uiautomator(value, **kwargs)
        else:
            raise ValueError('value值不对')

    def find_element_by_adaptor(self, value, **kwargs):
        """
        根据value的特征自动选择相适应的方法
        :param value: xpath...
        :param kwargs: 
        :return: MyElement对象
        """
        if r'//' in value or r'/' in value or '@' in value:
            return self.find_element_by_xpath(value, **kwargs)
        elif 'new UiSelector()' in value:
            return self.find_element_by_android_uiautomator(value, **kwargs)
        else:
            raise ValueError('value值不对')

    def find_element_and_click(self, value, expect_element=EXPECT_ELEMENT, max_retries=MAX_RETRIES,
                               click_wait_time=CLICK_WAIT_TIME, exponential_base=EXPONENTIAL_BASE,
                               relation='or', rtn=1, **kwargs):
        """
                点击元素。
                若expect_element的是列表，当relation值是'or'时，默认返回第一个找到的元素；当relation值是'and'时,必须找到所有元素，返回第rtn个元素。
                若expect_element的值是'page_source'，则比较点击后的page_source的值，如果不同则认为点击成功
                若expect_element的值是目标元素的xpath等，则点击后自动用相适应的方法找目标元素，如果找到了则认为点击成功
                若expect_element是None，只是单纯点击，不关心点击后效果。
                :param value: 要找的元素的Xpath或则其他定位信息
                :param expect_element: 取值page_source（默认）, 期望点击后出现的元素的Xpath或则其他定位信息，或者None。
                :param max_retries: 最大重试次数
                :param click_wait_time: 第一次点击后的等待时间
                :param exponential_base: 等待时间的相关参数，等待时间=wait_time * exponential_base ** times
                :param relation: 取值为'and'或者'or', 当expect_element为列表时需要用到
                :param rtn: 取值为整数，当expect_element有多个元素时需要根据rtn参数决定返回第几个元素。rtn=0时返回self
                :param kwargs:  其他参数，最终会传到Retry装饰器里面
                :return: self或者MyElement对象
                """
        raise_exception = kwargs.get('raise_exception', True)
        kwargs['raise_exception'] = False
        for times in range(max_retries + 1):
            element = self.find_element_by_adaptor(value, **kwargs)
            if element:
                expect = element.click(expect_element=expect_element, max_retries=0,
                                       click_wait_time=click_wait_time,  exponential_base=exponential_base,
                                       relation=relation, rtn=rtn, **kwargs)
                if expect:
                    return expect
                elif times == max_retries:
                    print('点击元素【%s】后,未找到期望出现的元素:%s' % (value, expect_element))
        if raise_exception:
            raise NoSuchElementException

    @property
    def page_source(self):
        return self.driver.page_source

    def get_window_size(self):
        return self.driver.get_window_size()

    def swipe(self, start_x, start_y, end_x, end_y, duration=None,
              expect_element=EXPECT_ELEMENT, max_retries=MAX_RETRIES,
              swipe_wait_time=SWIPE_WAIT_TIME, relation='or', rtn=1, **kwargs):
        """
        执行滑动动作
        若expect_element的是列表，当relation值是'or'时，默认返回第一个找到的元素；当relation值是'and'时,必须找到所有元素，返回第trn个元素。
        若expect_element的值是'page_source'，则比较滑动后的page_source的值，如果不同则认为滑动成功
        若expect_element的值是目标元素的xpath等，则滑动后自动用相适应的方法找目标元素，如果找到了则认为滑动成功
        若expect_element是None，只是单纯执行滑动动作，不关心滑动后效果。
        :param start_x: 
        :param start_y: 
        :param end_x: 
        :param end_y: 
        :param duration: 
        :param expect_element: 取值page_source（默认）, 目标元素Xpath，或者None。
        :param max_retries: 最大重试次数
        :param swipe_wait_time: 滑动后等待时间
        :param relation: 取值为'and'或者'or', 当expect_element为列表时需要用到
        :param rtn: 取值为整数，当expect_element有多个元素时需要根据rtn参数决定返回第几个元素。rtn=0时返回self
        :param kwargs: 其他参数，最终会传到Retry装饰器里面
        :return: self或者MyElement对象
        """
        raise_exception = kwargs.get('raise_exception', True)
        kwargs['raise_exception'] = True
        if isinstance(expect_element, list):
            if relation == 'or':
                for times in range(max_retries+1):
                    self.driver.swipe(start_x, start_y, end_x, end_y, duration)
                    time.sleep(swipe_wait_time)
                    flag = False
                    for value in expect_element:
                        try:
                            element = self.find_element_by_adaptor(value, **kwargs)
                            flag = True
                            break
                        except NoSuchElementException:
                            pass
                    if flag:
                        if rtn == 1:
                            return element
                        elif rtn == 0:
                            return self
                        else:
                            raise ValueError('rtn值不对')
                if raise_exception:
                    raise Exception('执行滑动操作后, 未找到元素列表:%s中的任一元素' % str(expect_element))
            elif relation == 'and':
                for times in range(max_retries+1):
                    self.driver.swipe(start_x, start_y, end_x, end_y, duration)
                    time.sleep(swipe_wait_time)
                    elements = list()
                    for value in expect_element:
                        try:
                            element = self.find_element_by_adaptor(value, **kwargs)
                            elements.append(element)
                        except NoSuchElementException:
                            elements = list()
                            break
                    if elements:
                        if rtn == 0:
                            return self
                        else:
                            return elements[rtn - 1]
                if raise_exception:
                    raise Exception('执行滑动操作后, 未找到元素列表:%s中的全部元素' % str(expect_element))
            else:
                raise ValueError('relation值不对')
        elif expect_element == 'page_source':
            page_source = self.page_source
            for times in range(max_retries + 1):
                self.driver.swipe(start_x, start_y, end_x, end_y, duration)
                time.sleep(swipe_wait_time)
                if self.page_source != page_source:
                    return self
            if raise_exception:
                raise Exception('执行滑动操作后,页面无变化')
        elif expect_element is not None:
            for times in range(max_retries+1):
                self.driver.swipe(start_x, start_y, end_x, end_y, duration)
                time.sleep(swipe_wait_time)
                try:
                    return self.find_element_by_adaptor(expect_element, **kwargs)
                except NoSuchElementException:
                    pass
            if raise_exception:
                raise NoSuchElementException('执行滑动操作后,未找到期望出现的元素:%s' % expect_element)
        else:
            self.driver.swipe(start_x, start_y, end_x, end_y, duration)
            time.sleep(swipe_wait_time)
            return self

    @expectation
    def keyevent(self, keycode, metastate=None, **kwargs):
        self.driver.keyevent(keycode, metastate)

    @expectation
    def adb_tap(self, position=None, element_key: str=None, position_dict=None,  **kwargs):
        if not self.serial:
            raise RuntimeError('MyDriver对象初始化时没有传参数serial')
        if position is None:
            position = position_dict[element_key]
            os.system(
            "adb -s %s shell input tap %d %d" % (self.serial, position[0], position[1]))

    def ai_click(self, value, position_dict=None, **kwargs):
        if position_dict is None:
            position_dict = self.position_dict
        if position_dict is None or value not in position_dict:
            return self.find_element_and_click(value, position_dict=position_dict, **kwargs)
        else:
            self.adb_tap(element_key=value, position_dict=position_dict, **kwargs)

    def ai_send_keys(self, value, content, position_dict=None, **kwargs):
        if position_dict is None:
            position_dict = self.position_dict
        if position_dict is None or value not in position_dict:
            my_element = self.find_element_by_xpath(value, position_dict=position_dict, **kwargs)
            my_element.send_keys(content)
            return my_element
        else:
            self.adb_tap(element_key=value, position_dict=position_dict, **kwargs)
            self.adb_input_text(content)

    def adb_input_text(self, text, length=None):
        length = length if length is not None else len(text)
        if self.serial:
            self.driver.keyevent(123)
            for n in range(length+3):
                self.driver.keyevent(67)
            os.system(
                'adb -s {} shell input text {}'.format(self.serial, text)
            )
        else:
            raise RuntimeError('MyDriver对象初始化时没有传参数serial')

    @RETRY.retry_until_done_or_timeout
    def find_element(self, by=By.ID, value=None, element_name=None, **kwargs):
        element_name = element_name if element_name else value
        element = self.driver.find_element(by, value)
        return MyElement(element, element_name, self)

    @RETRY.retry_until_done_or_timeout
    def find_elements(self, by=By.ID, value=None, element_name=None, **kwargs):
        element_name = element_name if element_name else value
        elements = self.driver.find_elements(by, value)
        return (MyElement(element, element_name, self) for element in elements)

    def is_element_present(self, by=By.ID, value=None, element_name=None,
                           is_element_present_timeout=IS_ELEMENT_PRESENT_TIMEOUT) -> bool:
        try:
            self.find_element(by, value, element_name, timeout=is_element_present_timeout,
                              raise_exception=True, prompt=False)
            return True
        except (NoSuchElementException, Exception):
            return False

    def back(self, times=1, expect_element=EXPECT_ELEMENT, max_retries=MAX_RETRIES,
             back_wait_time=BACK_WAIT_TIME,  relation='or', rtn=1, **kwargs):
        raise_exception = kwargs.get('raise_exception', True)
        kwargs['raise_exception'] = True
        for n in range(times-1):
            self.driver.back()
            time.sleep(back_wait_time)
        if isinstance(expect_element, list):
            if relation == 'or':
                for times in range(max_retries + 1):
                    self.driver.back()
                    time.sleep(back_wait_time)
                    flag = False
                    for value in expect_element:
                        try:
                            element = self.find_element_by_adaptor(value, **kwargs)
                            flag = True
                            break
                        except NoSuchElementException:
                            pass
                    if flag:
                        if rtn == 1:
                            return element
                        elif rtn == 0:
                            return self
                        else:
                            raise ValueError('rtn值不对')
                if raise_exception:
                    raise Exception('执行返回操作后, 未找到元素列表:%s中的任一元素' % str(expect_element))
            elif relation == 'and':
                for times in range(max_retries + 1):
                    self.driver.back()
                    time.sleep(back_wait_time)
                    elements = list()
                    for value in expect_element:
                        try:
                            element = self.find_element_by_adaptor(value, **kwargs)
                            elements.append(element)
                        except NoSuchElementException:
                            elements = list()
                            break
                    if elements:
                        if rtn == 0:
                            return self
                        else:
                            return elements[rtn - 1]
                if raise_exception:
                    raise Exception('执行返回操作后, 未找到元素列表:%s中的全部元素' % str(expect_element))
        elif expect_element == 'page_source':
            page_source = self.page_source
            for times in range(max_retries+1):
                self.driver.back()
                time.sleep(back_wait_time)
                if self.page_source != page_source:
                    return self
            if raise_exception:
                raise Exception('执行返回操作后,页面无变化')
        elif expect_element is not None:
            for times in range(max_retries + 1):
                self.driver.back()
                time.sleep(back_wait_time)
                try:
                    return self.find_element_by_adaptor(expect_element, **kwargs)
                except NoSuchElementException:
                    pass
            if raise_exception:
                raise NoSuchElementException('执行返回操作后,未找到期望出现的元素:%s' % expect_element)
        else:
            self.driver.back()
            time.sleep(back_wait_time)
            return self

    def quit(self):
        self.driver.quit()


class MyElement(object):
    def __init__(self, web_element, element_name, mydriver):
        self.element = web_element
        self.name = element_name
        self.driver = mydriver

    def send_keys(self, content, max_retries=MAX_RETRIES, raise_exception=True, wait_for_check_when_error_occur=0):
        self.element.send_keys(content)
        for retry_times in range(max_retries):
            element_content = self.element.text
            if element_content == content:
                return self
            elif element_content == '':
                print('text属性无法获取输入文本内容，无法校验')
                return self
            else:
                if len(element_content) < len(content) and element_content == content[:len(element_content)]:
                    print('输入的文本不完整，将自动补全余下文本…')
                    self.element.send_keys(content[len(element_content) - len(content):])
                else:
                    print('输入框的内容不正确，将清空后重新输入…')
                    self.element.clear()
                    self.element.send_keys(content)
        element_content = self.element.text
        if element_content == content:
            return self
        elif element_content == '':
            print('text属性无法获取输入文本内容，无法校验')
            return self
        elif raise_exception:
            raise Exception('element【%s】:send keys failed' % self.name)
        else:
            print('输入框的内容不正确,请检查')
            time.sleep(wait_for_check_when_error_occur)
            return self

    def click(self, expect_element=EXPECT_ELEMENT, max_retries=MAX_RETRIES, click_wait_time=CLICK_WAIT_TIME,
              exponential_base=EXPONENTIAL_BASE, relation='or', rtn=1, **kwargs):
        """
        点击元素。
        若expect_element的是列表，当relation值是'or'时，默认返回第一个找到的元素；当relation值是'and'时,必须找到所有元素，返回第rtn个元素。
        若expect_element的值是'page_source'，则比较点击后的page_source的值，如果不同则认为点击成功
        若expect_element的值是目标元素的xpath等，则点击后自动用相适应的方法找目标元素，如果找到了则认为点击成功
        若expect_element是None，只是单纯点击，不关心点击后效果。
        :param expect_element: 取值page_source（默认）, 目标元素Xpath，或者None。
        :param max_retries: 最大重试次数
        :param click_wait_time: 第一次点击后的等待时间
        :param exponential_base: 等待时间的相关参数，等待时间=wait_time * exponential_base ** times
        :param relation: 取值为'and'或者'or', 当expect_element为列表时需要用到
        :param rtn: 取值为整数，当expect_element有多个元素时需要根据rtn参数决定返回第几个元素。rtn=0时返回self
        :param kwargs:  其他参数，最终会传到Retry装饰器里面
        :return: self或者MyElement对象
        """
        raise_exception = kwargs.get('raise_exception', True)
        kwargs['raise_exception'] = True
        if isinstance(expect_element, list):
            if relation == 'or':
                for times in range(max_retries+1):
                    self.element.click()
                    time.sleep(click_wait_time * exponential_base ** times)
                    flag = False
                    for value in expect_element:
                        try:
                            element = self.driver.find_element_by_adaptor(value, **kwargs)
                            flag = True
                            break
                        except NoSuchElementException:
                            pass
                    if flag:
                        if rtn == 1:
                            return element
                        elif rtn == 0:
                            return self
                        else:
                            raise ValueError('rtn值不对')
                if raise_exception:
                    raise Exception('点击后, 未找到元素列表:%s中的任一元素' % str(expect_element))
            elif relation == 'and':
                for times in range(max_retries+1):
                    self.element.click()
                    time.sleep(click_wait_time * exponential_base ** times)
                    elements = list()
                    for value in expect_element:
                        try:
                            element = self.driver.find_element_by_adaptor(value, **kwargs)
                            elements.append(element)
                        except NoSuchElementException:
                            elements = list()
                            break
                    if elements:
                        if rtn == 0:
                            return self
                        else:
                            return elements[rtn-1]
                if raise_exception:
                    raise Exception('点击后, 未找到元素列表:%s中的全部元素' % str(expect_element))
            else:
                raise ValueError('relation值不对')
        elif expect_element == 'page_source':
            page_source = self.element.parent.page_source
            for times in range(max_retries+1):
                self.element.click()
                time.sleep(click_wait_time * exponential_base ** times)
                if self.element.parent.page_source != page_source:
                    return self
            if raise_exception:
                raise Exception('点击元素【%s】后,未找到期望出现的元素:%s' % (self.name, expect_element))
        elif expect_element is not None:
            for times in range(max_retries+1):
                self.element.click()
                time.sleep(click_wait_time * exponential_base ** times)
                try:
                    return self.driver.find_element_by_adaptor(expect_element, **kwargs)
                except NoSuchElementException:
                    pass
            if raise_exception:
                raise NoSuchElementException('点击元素【%s】后,未找到期望出现的元素:%s' % (self.name, expect_element))
        else:
            self.element.click()
            time.sleep(click_wait_time)
            return self

    def clear(self):
        self.element.clear()
        return self

    @property
    def text(self):
        return self.element.text

    def set_text(self, keys=''):
        self.element.set_text(keys)

    def set_value(self, value, raise_excetion=True, prompt=True):
        try:
            self.element.set_value(value)
        except Exception as e:
            if prompt:
                print(e)
                print_exc()
            if raise_excetion:
                raise

    def get_center_position(self):
        rect = self.element.rect
        x_center = int(rect['x']+rect['width']/2)
        y_center = int(rect['y']+rect['height']/2)
        return x_center, y_center

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} (session="{1}", element="{2}")>'.format(
            type(self), self.element.parent.session_id, self.element.id)
