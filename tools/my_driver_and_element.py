from config import SENTRY
from selenium.common.exceptions import NoSuchElementException
from appium.webdriver.common.touch_action import TouchAction
import time
from selenium.webdriver.common.by import By
import sys
from appium_robot.robot.tools.retry import Retry
from appium_robot.robot.tools.function_tools import set_logger
from functools import wraps
from traceback import print_exc
import os
import re
import random

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
MAX_RETRIES = 1
CLICK_WAIT_TIME = 0.8
EXPONENTIAL_BASE = 1
EXPECT_ELEMENT = None
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
    print(path_position, '导入相关参数配置：')
    for g in ['RETRY', 'MAX_RETRIES', 'CLICK_WAIT_TIME', 'EXPONENTIAL_BASE',
              'IS_ELEMENT_PRESENT_TIMEOUT', 'SWIPE_WAIT_TIME', 'BACK_WAIT_TIME', 'EXPECT_ELEMENT']:
        try:
            exec("from %s import %s" % (path_position, g))
            print(f'导入 {g} 成功：{g}={eval(g)}')
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


def expectation(method, _expect_element=EXPECT_ELEMENT, _max_retries=MAX_RETRIES, _wait_time=1, _exponential_base=1,
                _relation='or', _rtn=1, _raise_exception=True):
    """
    功能：装饰一个方法，判断页面是否出现期望的元素，以此来判断该方法是否执行成功，如果成功，直接将期望的元素作为返回值
    若expect_element的值是目标元素的xpath等，则执行方法后自动用相适应的方法找目标元素，如果找到了则认为方法执行成功
    若expect_element的值是'page_source'，则比较执行方法后的page_source的值，如果不同则认为方法执行成功
    若expect_element的值是正则表达式，则执行方法后，在page_source中匹配该模式，如果匹配成功，则认为方法执行成功
    若expect_element的是列表，当relation值是'or'时，默认返回第一个找到的元素；当relation值是'and'时,必须找到所有元素，返回第rtn个元素。
    若expect_element是None，只是单纯执行方法动作，不关心方法执行后效果。
    :param method: 被装饰的方法
    :param _expect_element: str类型,值可以是'page_source', 正则表达式，目标元素Xpath等，或者None。
    :param _max_retries: 最大重试次数
    :param _wait_time: 第一次执行方法后的等待时间
    :param _exponential_base: 等待时间的相关参数，等待时间=wait_time * exponential_base ** times
    :param _relation: 取值为'and'或者'or', 当expect_element为列表时需要用到
    :param _rtn: 取值为整数，当expect_element有多个元素时需要根据rtn参数决定返回第几个元素。rtn=0时返回self
    :param _raise_exception: bool类型，当未发现期望元素时，根据_raise_exception的值确定是否抛出异常
    :return: MyDriver或者MyElement对象
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        expect_element = kwargs.get('expect_element', _expect_element)
        max_retries = kwargs.get('max_retries', _max_retries)
        wait_time = kwargs.get('wait_time', _wait_time)
        exponential_base = kwargs.get('exponential_base', _exponential_base)
        relation = kwargs.get('relation', _relation)
        rtn = kwargs.get('rtn', _rtn)
        raise_exception = kwargs.get('raise_exception', _raise_exception)
        kwargs['raise_exception'] = True
        driver = self if isinstance(self, MyDriver) else self.driver
        if isinstance(expect_element, str):
            if expect_element.startswith('/') or '[@' in expect_element or 'contains(@' in expect_element:
                for times in range(max_retries+1):
                    method(self, *args, **kwargs)
                    time.sleep(wait_time * exponential_base ** times)
                    try:
                        return driver.find_element_by_xpath(expect_element, **kwargs)
                    except NoSuchElementException:
                        pass
                if raise_exception:
                    raise NoSuchElementException(f'执行方法{method.__name__}后，未找到期望出现的元素:%s' % expect_element)
            elif expect_element == 'page_source':
                page_source = driver.page_source
                for times in range(max_retries + 1):
                    method(self, *args, **kwargs)
                    time.sleep(wait_time * exponential_base ** times)
                    if driver.page_source != page_source:
                        return self
                if raise_exception:
                    raise Exception(f'执行方法{method.__name__}后，页面无变化')
            elif 'new UiSelector' not in expect_element:
                for times in range(max_retries + 1):
                    method(self, *args, **kwargs)
                    time.sleep(wait_time * exponential_base ** times)
                    if re.search(expect_element, driver.page_source):
                        return self
                if raise_exception:
                    raise Exception(f'执行方法{method.__name__}后，页面未出现"{expect_element}"')
            else:
                for times in range(max_retries+1):
                    method(self, *args, **kwargs)
                    time.sleep(wait_time * exponential_base ** times)
                    try:
                        return driver.find_element_by_android_uiautomator(expect_element, **kwargs)
                    except NoSuchElementException:
                        pass
                if raise_exception:
                    raise NoSuchElementException(f'执行方法{method.__name__}后，未找到期望出现的元素:%s' % expect_element)
        elif isinstance(expect_element, list):
            if relation == 'or':
                for times in range(max_retries+1):
                    method(self, *args, **kwargs)
                    time.sleep(wait_time * exponential_base ** times)
                    flag = False
                    for value in expect_element:
                        try:
                            element = driver.find_element_by_xpath(value, **kwargs)
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
                    method(self, *args, **kwargs)
                    time.sleep(wait_time * exponential_base ** times)
                    elements = list()
                    for value in expect_element:
                        try:
                            element = driver.find_element_by_xpath(value, **kwargs)
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
        elif expect_element is None:
            method(self, *args, **kwargs)
            time.sleep(wait_time)
            return self
        else:
            raise ValueError('expect_element值必须为字符串或者元素类型为字符串的列表!')
    return wrapper


class MyDriver(object):
    """
    重新封装WebDriver的常用方法，使用retry装饰器和expectation装饰器。retry装饰器在定位元素失败时自动等待并重试，expectation装饰器
    一般用来装饰动作，根据期望的元素是否出现，来判断动作是否成功。
    关于expect_element:
    执行某个动作（滑动，返回，点击等）后，会预期页面出现某个元素，根据期望的元素是否出现，来判断动作是否成功。
    这个需求非常普遍，因此应当作为一个基本功能。
    """
    def __init__(self, web_driver, serial=None, position_dict=None, xpath_list=None):
        self.driver = web_driver
        self.serial = serial
        self.position_dict = position_dict
        self.xpath_list = xpath_list
        self.touch_action = TouchAction(self.driver)

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

    def find_element_by_text(self, text, element_name=None, **kwargs):
        """
        通过text属性值，在page_source内找到相应的html，进而生成xpath路径，再调用find_element_by_xpath方法定位元素
        :param text: 页面元素的文本内容
        :param element_name: 元素名称，可自定义
        :param kwargs: 其他参数，最终传给retry装饰器
        :return: MyElement
        """
        page_source = self.page_source
        matches = re.findall('<[.\w\\s\"=\[\]]*text="%s".*?>' % text, page_source, re.DOTALL)
        print(matches, ',', len(matches))
        if matches:
            outer_html = matches[0]
            class_name = outer_html.split(' ', maxsplit=1)[0][1:]
            xpath = f'//{class_name}[@text="{text}"]'
            print(xpath)
            return self.find_element_by_xpath(xpath, element_name=element_name, **kwargs)
        else:
            print(f'page_source中未发现"{text}",请检查是否输入有误')

    def find_element_by_partial_text(self, text, element_name=None, **kwargs):
        """
        通过text属性值，在page_source内找到相应的html，进而生成xpath路径，再调用find_element_by_xpath方法定位元素
        :param text: 页面元素的文本内容
        :param element_name: 元素名称，可自定义
        :param kwargs: 其他参数，最终传给retry装饰器
        :return: MyElement
        """
        page_source = self.page_source
        matches = re.findall('<[.\w\\s\"=\[\]]*?text="[^\"<>]*?%s[^\"<>]*?".*?>' % text, page_source, re.DOTALL)
        print(matches, ',', len(matches))
        if matches:
            outer_html = matches[0]
            class_name = outer_html.split(' ', maxsplit=1)[0][1:]
            xpath = f'//{class_name}[contains(@text, "{text}")]'
            print(xpath)
            return self.find_element_by_xpath(xpath, element_name=element_name, **kwargs)
        else:
            print(f'page_source中未发现"{text}",请检查是否输入有误')

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

    def find_element_and_click(self, value, expect_element=EXPECT_ELEMENT, max_retries=MAX_RETRIES,
                               wait_time=CLICK_WAIT_TIME, exponential_base=EXPONENTIAL_BASE,
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
                :param wait_time: 第一次点击后的等待时间
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
                                       wait_time=wait_time, exponential_base=exponential_base,
                                       relation=relation, rtn=rtn, **kwargs)
                if expect:
                    return expect
                elif times == max_retries:
                    print('点击元素【%s】后,未找到期望出现的元素:%s' % (value, expect_element))
        if raise_exception:
            raise NoSuchElementException(f'find_element_and_click方法出错，未定位到元素: {value}')

    @property
    def page_source(self):
        return self.driver.page_source

    def detect_page_source(self, target: str, poll_frequency=1, exponential_base=1, max_tries=3) -> bool:
        """
        功能：检查page_source是否出现给定的文本
        :param target: 正则表达式，匹配目标文本
        :param poll_frequency: 重试频率
        :param exponential_base: 指数底数，决定等待时间。
        :param max_tries: 最大检查次数
        :return: True 或 False
        """
        for times in range(max_tries):
            if re.search(target, self.page_source):
                print(f"target:{target} detected")
                return True
            if times < max_tries-1:
                time.sleep(poll_frequency * exponential_base ** times)
        print(f"target:{target} not detected")
        return False

    def get_current_activity(self, poll_frequency=1, duration=6, max_time=8):
        current_activity = self.driver.current_activity
        _start_time = start_time = time.time()
        while True:
            time.sleep(poll_frequency)
            if self.driver.current_activity != current_activity:
                current_activity = self.driver.current_activity
                start_time = time.time()
            elif time.time() - start_time > duration:
                break
            if time.time() - _start_time > max_time:
                break
        return current_activity

    def write_page_source_to_xml(self, file_path, error=None):
        """
        把page_source写入xml文件
        :param file_path: xml文件路径(包含文件名称)
        :param error: 捕获到的异常
        :return: self
        """
        if not file_path.endswith('.xml'):
            file_path += '.xml'
        if error:
            logger_fh = set_logger(log_file_path=file_path, output=False, name='my_driver_and_element')
            logger_fh.exception("Exception Logged")
        page_source = self.driver.page_source
        with open(file_path, 'a+') as f:
            if error:
                f.write('\n2222222222222222222222222222222\n')
                f.write(error.__repr__()+'\n')
                f.write('2222222222222222222222222222222\n')
            f.write(self.driver.current_activity+'\n')
            f.write(page_source)
        print(f'page_source已写入文件：{file_path}, 赶紧查看')
        return self

    def get_window_size(self):
        return self.driver.get_window_size()

    @expectation
    def swipe(self, start_x, start_y, end_x, end_y, duration=None, wait_time=SWIPE_WAIT_TIME, **kwargs):
        """
        执行滑动动作
        :param start_x: 滑动起始位置横坐标
        :param start_y: 滑动起始位置纵坐标
        :param end_x: 滑动结束位置横坐标
        :param end_y: 滑动结束位置纵坐标
        :param duration: 滑动操作持续时间
        :param wait_time: 第一次的滑动后等待时间
        :param kwargs: 其他参数，最终会传到Retry装饰器里面
        :return: self或者MyElement对象
        """
        self.driver.swipe(start_x, start_y, end_x, end_y, duration)

    @expectation
    def swipe_up(self, distance, duration=None, wait_time=SWIPE_WAIT_TIME, **kwargs):
        """
        屏幕上滑操作(通用接口)
        """
        self.driver.swipe(300, 300 + int(distance), 300, 300, duration=duration)
        time.sleep(3)

    @expectation
    def swipe_down(self, distance, duration=None, wait_time=SWIPE_WAIT_TIME, **kwargs):
        """
        屏幕下滑操作(通用接口)
        """
        self.driver.swipe(300, 300, 300, 300 + int(distance), duration=duration)
        time.sleep(3)

    @expectation
    def keyevent(self, keycode, metastate=None, **kwargs):
        self.driver.keyevent(keycode, metastate)

    @expectation
    def tap(self, x, y, count=1, wait_time=CLICK_WAIT_TIME, **kwargs):
        self.touch_action.tap(x=x, y=y, count=count).perform()

    @expectation
    def adb_tap(self, position=None, element_key: str=None, position_dict=None, wait_time=CLICK_WAIT_TIME, **kwargs):
        if not self.serial:
            raise RuntimeError('MyDriver对象初始化时没有传参数serial')
        if position is None:
            position = position_dict[element_key]
        os.system(
            "adb -s %s shell input tap %d %d" % (self.serial, position[0], position[1]))

    def ai_click(self, value, position_dict=None, **kwargs):
        """
        功能：第一次定位元素时，调用find_element_and_click方法，同时将元素的位置写入position_dict（将value作为元素的key），
        以后再次调用该方法时，将使用adb tap命令，点击位置从position_dict获取。
        适用范围：适用于某个元素的xpath在脚本中唯一并且该元素的位置固定的情况
        :param value: 元素的xpath
        :param position_dict: 位置字典， 值为value所对应的元素的中心坐标
        :param kwargs: 其他参数，比如expect_element, timeout等
        :return: MyElement对象或者self
        """
        if position_dict is None:
            position_dict = self.position_dict
        if position_dict is None or value not in position_dict:
            return self.find_element_and_click(value, position_dict=position_dict, **kwargs)
        else:
            return self.adb_tap(element_key=value, position_dict=position_dict, **kwargs)

    def ai_send_keys(self, value, content, position_dict=None, length=None, check=False, max_retries=2, **kwargs):
        """
        功能：参考ai_click的功能说明
        """
        raise_exception = kwargs.get('raise_exception', True)
        if position_dict is None:
            position_dict = self.position_dict
        if position_dict is None or value not in position_dict:
            my_element = self.find_element_by_xpath(value, position_dict=position_dict, **kwargs)
            if check:
                return my_element.send_keys(content, raise_exception=raise_exception)
            else:
                return my_element.element.send_keys(content)
        else:
            kwargs['expect_element'] = None
            self.adb_tap(element_key=value, position_dict=position_dict, **kwargs)
            self.adb_input_text(content, length)
            if check:
                position = position_dict[value]
                if re.search('(\[@text=([\"\'])).*(\\2\])$', value):
                    value = re.sub('(\[@text=([\"\'])).*(\\2\])$', '\\1%s\\3' % content, value)
                else:
                    if self.driver.find_element_by_xpath(value).text == '':
                        print('text属性无法获取输入文本内容，无法校验')
                        return self
                    if "'" in value:
                        if value.endswith(']'):
                            value = value[:-1]+" and @text='%s']" % content
                        else:
                            value += "[@text='%s']" % content
                    else:
                        if value.endswith(']'):
                            value = value[:-1]+' and @text="%s"]' % content
                        else:
                            value += '[@text="%s"]' % content
                print('check 元素：', value)
                for _ in range(max_retries):
                    try:
                        self.driver.find_element_by_xpath(value)
                        return self
                    except NoSuchElementException:
                        self.adb_tap(element_key=value, position_dict=position_dict, **kwargs)
                        self.adb_input_text(content, length)
                print(f'ai_send_keys failed：value={value}, content={content}, position={position}')
                if raise_exception:
                    raise NoSuchElementException('未发现元素【%s】' % value)
            else:
                return self

    def adb_input_text(self, text, length=None):
        length = length if length is not None else 0
        if self.serial:
            self.driver.keyevent(123)
            for n in range(length):
                self.driver.keyevent(67)
            os.system(
                'adb -s {} shell input text {}'.format(self.serial, text)
            )
        else:
            raise RuntimeError('MyDriver对象初始化时没有传参数serial')
        return self

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

    @expectation
    def _back(self, wait_time=BACK_WAIT_TIME, **kwargs):
        self.driver.back()

    def back(self, times=1, wait_time=BACK_WAIT_TIME, **kwargs):
        """
        返回上一页面
        :param times: 返回次数
        :param wait_time: 等待时间
        :param kwargs: 
        :return: 
        """
        for n in range(times-1):
            self.driver.back()
            time.sleep(wait_time)
        return self._back(wait_time=wait_time, **kwargs)

    def quit(self):
        self.driver.quit()


class MyElement(object):
    """
    重新封装WebElement的常用方法，使用expectation装饰器。expectation装饰器用来装饰动作，根据期望的元素是否出现，来判断动作是否成功。
    """
    def __init__(self, web_element, element_name, my_driver):
        self.element = web_element
        self.name = element_name
        self.driver = my_driver
        self.touch_action = TouchAction(self.driver.driver)

    @RETRY.retry_until_done_or_timeout
    def find_element_by_xpath(self, xpath, element_name=None, position_dict=None, xpath_list=None, **kwargs):
        """串联定位"""
        if position_dict is None:
            position_dict = self.driver.position_dict
        if xpath_list is None:
            xpath_list = self.driver.xpath_list
        element_name = element_name if element_name else xpath
        element = self.element.find_element_by_xpath(xpath)
        my_element = MyElement(element, element_name, self.driver)
        if position_dict is not None and isinstance(position_dict, dict):
            position_dict[xpath] = my_element.get_center_position()
        if xpath_list is not None and isinstance(xpath_list, list):
            xpath_list.append(xpath)
        return my_element

    def send_keys(self, content, max_retries=MAX_RETRIES, raise_exception=True, wait_for_check_when_error_occur=15):
        self.element.send_keys(content)
        for retry_times in range(max_retries+1):
            element_content = self.element.text
            if element_content == content:
                return self
            elif element_content == '':
                print('text属性无法获取输入文本内容，无法校验')
                return self
            else:
                print('输入框的内容不正确，将清空后重新输入…')
                self.element.clear().send_keys(content)
                # if len(element_content) < len(content) and element_content == content[:len(element_content)]:
                #     print('输入的文本不完整，将自动补全余下文本…')
                #     self.element.send_keys(content[len(element_content) - len(content):])
                # else:
                #     print('输入框的内容不正确，将清空后重新输入…')
                #     self.element.clear()
                #     self.element.send_keys(content)
        print(f'send_keys方法输入内容不正确，content:{content}, len(content):{len(content)}，'
              f'element_content:{element_content}, len(element_content):{len(element_content)}')
        time.sleep(wait_for_check_when_error_occur)
        if raise_exception:
            raise Exception('element【%s】:send keys failed' % self.name)
        else:
            return self

    @expectation
    def click(self, wait_time=CLICK_WAIT_TIME, exponential_base=EXPONENTIAL_BASE, **kwargs):
        """
        点击元素。
        :param wait_time: 第一次点击后的等待时间
        :param exponential_base: 等待时间的相关参数，等待时间=wait_time * exponential_base ** times
        :param kwargs: 其他参数，最终会传到Retry装饰器里面
        :return: self或者MyElement对象
        """
        self.element.click()

    def clear(self):
        self.element.clear()
        return self

    @property
    def text(self):
        return self.element.text

    def set_text(self, keys=''):
        self.element.set_text(keys)

    def set_value(self, value, raise_exception=True, prompt=True):
        try:
            self.element.set_value(value)
        except Exception as e:
            if prompt:
                print(e)
                print_exc()
            if raise_exception:
                raise

    def get_center_position(self):
        rect = self.element.rect
        x_center = int(rect['x']+rect['width']/2)
        y_center = int(rect['y']+rect['height']/2)
        return x_center, y_center

    @expectation
    def tap(self, times, wait_time=2, **kwargs):
        """
        点击元素
        :param times: 点击次数
        :param wait_time: 完成点击动作后等待时间
        :param kwargs: 其他参数，传到装饰器中
        :return: 由参数expect_element的值和实际情况(是否定位到元素)决定
        """
        x, y = self.get_center_position()
        self.touch_action.tap(x=x, y=y, count=times).perform()

    @expectation
    def multi_tap(self, tap_counts_order: list, interval_between_taps=0.5, random_mode=True, wait_time=2, **kwargs):
        """
        功能：多次点击某个元素
        按照tap_counts_order顺序点击，比如tap_counts_order=[1,1,2]时，先点击1次，再点击1次，最后点击2次。
        :param tap_counts_order: list类型，点击次数序列
        :param interval_between_taps: 相邻两次点击之间的间隔
        :param random_mode: bool类型是否随机选择点击位置
        :param wait_time: 完成所有点击动作后的等待时间
        :param kwargs: 其他参数，传到装饰器中
        :return: 由参数expect_element的值和实际情况(是否定位到元素)决定
        """
        rect = self.element.rect
        x = int(rect['x'])
        y = int(rect['y'])
        width = int(rect['width'])
        height = int(rect['height'])
        x_center = int(rect['x'] + rect['width'] / 2)
        y_center = int(rect['y'] + rect['height'] / 2)
        if random_mode:
            for count in tap_counts_order:
                x_to_tap = x + random.choice(range(1, width))
                y_to_tap = y + random.choice(range(1, height))
                self.touch_action.tap(x=x_to_tap, y=y_to_tap, count=count).perform().\
                    wait(interval_between_taps*1000).perform()
        else:
            for count in tap_counts_order:
                self.touch_action.tap(x=x_center, y=y_center, count=count).perform(). \
                    wait(interval_between_taps * 1000).perform()

    def save_image(self, file_name='1.png', serial=None):
        from PIL import Image
        from utils import ARCHIVE_PATH
        serial = serial or self.driver.serial
        if not serial:
            raise ValueError('serial为None！')
        image_path = file_name if file_name.startswith('/') else os.path.join(ARCHIVE_PATH, file_name)
        pull_to_dir_path, file_name = os.path.split(image_path)
        # 截图保存到设备里
        os.system(f'adb -s {serial} shell screencap -p /sdcard/{file_name}')
        # pull到电脑
        os.system(f'adb -s {serial} pull /sdcard/{file_name} {pull_to_dir_path}')
        img = Image.open(image_path)
        rect = self.element.rect
        box = rect['x'], rect['y'], rect['x'] + rect['width'], rect['y'] + rect['height']
        cropped = img.crop(box)
        cropped.save(image_path)
        print(f'保存element图片到文件 {image_path}     ok')

    def __repr__(self):
        return '<{0.__module__}.{0.__name__} (session="{1}", element="{2}")>, element_name="{3}"'.format(
            type(self), self.element.parent.session_id, self.element.id, self.name)
