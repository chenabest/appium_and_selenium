#!/usr/bin/python3
# achen 2020/1/11 1:32 PM
# appium_functools

from config import SENTRY
from config import ARCHIVE_PATH
from appium_robot.robot.tools.function_tools import *
from appium_robot.robot import serial_port
from appium import webdriver
from utils import kill_server, start_server
import asyncio
import signal
import subprocess
from threading import Thread
import socket
from appium_robot.robot.wechat_work.setting import XPATH_OBJECT_ALL_VERSIONS


def init_driver(serial=None, appPackage="com.tencent.mm", appActivity=".ui.LauncherUI"):
    """功能：生成driver对象"""
    flag = socket.gethostname() == 'achens-iMac.lan'
    serial = get_valid_serial(serial)
    port = serial_port.get(serial, None)
    if not port:
        if flag:
            print('serial_port中没有配置该手机的端口号，将自动获取端口号...')
            port = get_valid_port()
            print('获取到的端口号为：%s' % port)
        else:
            raise RuntimeError(f'{serial} 文件{PROJECT_PATH}/appium_robot/robot/__init__.py中没有配置该手机的端口号！')
    print(serial, port)
    desired_caps = {
        "platformName": "Android",
        "deviceName": serial,
        "udid": serial,
        "systemPort": port + 4000,
        "appPackage": appPackage,
        "appActivity": appActivity,
        "noReset": "True",
        "unicodeKeyboard": "True",
        "resetKeyboard": "True",
        "newCommandTimeout": 6000,
    }
    for _ in range(6):
        try:
            kill_server(serial, get_run_file_name())
            time.sleep(3)
            start_server(serial, port)
            time.sleep(10)
            driver_server = 'http://localhost:{port}/wd/hub'.format(port=port)
            driver = webdriver.Remote(driver_server, desired_caps)
            time.sleep(15)
            return driver
        except Exception as e:
            print(e.__repr__())
            print_exc()
            if flag:
                port = get_valid_port()
                print('新端口号：%s' % port)
            print(serial, port)
            time.sleep(6)


def lock_screen(serial):
    print(os.popen(f'adb -s {serial} shell input keyevent 26').read())


def air_plane(state, serial):
    """
    开启或者关闭飞行模式
    :param state: 值为Tue时开启飞行模式，False时关闭飞行模式
    :param serial: 手机序列号
    :return: None
    """
    if state:
        subprocess.getoutput(
            'adb -s %s shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true' % serial)
    else:
        subprocess.getoutput(
            'adb -s %s shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false' % serial)
    time.sleep(5)


def swipe_up(driver, distance):
    """
    屏幕上滑操作(通用接口)
    """
    driver.swipe(300, 300 + int(distance), 300, 300)
    time.sleep(3)


def swipe_down(driver, distance):
    """
    屏幕下滑操作(通用接口)
    """
    driver.swipe(300, 300, 300, 300 + int(distance))
    time.sleep(3)


def detect_page_source(target: str, driver, poll_frequency=2, exponential_base=2, max_tries=3):
    for i in range(max_tries):
        if re.search(target, driver.page_source):
            print(f"target:{target} detected")
            return True
        if i < max_tries - 1:
            time.sleep(poll_frequency * exponential_base ** i)
    print(f"target:{target} not detected")
    return False


def get_current_activity(driver, poll_frequency=2, duration=6, max_time=8):
    current_activity = driver.current_activity
    _start_time = start_time = time.time()
    while True:
        time.sleep(poll_frequency)
        if driver.current_activity != current_activity:
            current_activity = driver.current_activity
            start_time = time.time()
        elif time.time() - start_time > duration:
            break
        if time.time() - _start_time > max_time:
            break
    return current_activity


def wechat_login(driver, account, password, wait_time=20):
    """
    微信自动登录
    :param driver: MyDriver对象
    :param account: 微信号
    :param password: 密码
    :param wait_time: 
    :return: 
    """
    while "正在载入数据" in driver.page_source:
        time.sleep(30)
    while '允许' in driver.page_source:
        driver.find_element_by_text('允许').click()
    match = re.search('登录|密码', driver.page_source)
    if match:
        print('登录...')
        if match.group() == '登录':
            # driver.find_element_by_text('登录').click()
            driver.find_element_by_xpath('//android.widget.Button[@text="登录"]').click(
                expect_element='//android.widget.Button[contains(@text, "用微信号")]'
            ).click().driver.ai_send_keys(
                '//android.widget.EditText[contains(@text, "微信号")]',
                content=account
            )
        driver.find_element_by_xpath(
            '//android.widget.EditText[contains(@text, "密码")]').element.send_keys(password)
        driver.find_element_and_click(
            '//android.widget.Button[@text="登录"]', wait_time=3)
        if "登录失败" in driver.page_source:
            print("登录失败")
            return False
        else:
            print("正在登录" in driver.page_source)
            while "正在登录" in driver.page_source:
                time.sleep(5)
            time.sleep(wait_time)
            print("登录成功")
            while "允许" in driver.page_source:
                driver.find_element_by_partial_text("允许").click(wait_time=3)
            if "否" in driver.page_source:
                driver.find_element_by_text("否").click()
            if "取消" in driver.page_source:
                driver.find_element_by_partial_text("取消").click()
            print("正在载入数据" in driver.page_source)
            while not driver.find_element_by_xpath(
                    '//android.widget.TextView[@text="通讯录"]',
                    raise_exception=False, prompt=False):
                if "取消" in driver.page_source:
                    driver.find_element_by_partial_text("取消").click()
                time.sleep(30)
            return True


def wechat_switch(serial, user=999):
    """
    功能：在主微信与分身微信之间切换
    :param serial: 序列号
    :param user: 999表示分身, 0表示原用户
    :return: 
    """
    cmd = "adb -s {} shell am start --user {} " \
          "-n com.tencent.mm/.ui.LauncherUI".format(serial, user)
    os.system(cmd)
    time.sleep(10)


def wechat_close_new_message_notification(driver):
    """
    功能：关闭微信新消息提醒
    :param driver: MyDriver对象
    :return: 
    """
    print("关闭新消息提醒...")
    driver.ai_click(
        '//android.widget.TextView[@text="我"]',
        expect_element='//android.widget.TextView[@text="设置"]'
    ).click(
        expect_element='//android.widget.TextView[@text="新消息提醒"]'
    ).click()
    driver.find_element_and_click(
        '//android.widget.TextView[@text="接收新消息通知"]/../../android.view.View[@content-desc="已开启"]',
        max_retries=0,
        timeout=1.5,
        raise_exception=False,
        prompt=False
    )
    if driver.find_element_and_click(
            '//android.widget.TextView[@text="接收语音和视频通话邀请通知"]/../../android.view.View[@content-desc="已开启"]',
            max_retries=0,
            timeout=1.5,
            raise_exception=False,
            prompt=False
    ):
        driver.find_element_by_text("确认关闭", raise_exception=False).click(expect_element=None)
    target = driver.back(2, expect_element='//android.widget.TextView[@text="微信"]')
    if target:
        target.click()
    print("关闭新消息提醒完成")


def clear_memory(driver, messenger=None):
    """
    当手机存储空间不足时清理内存
    :param driver: MyDriver或者WebDriver对象
    :param messenger: 信使，发送微信消息通知
    :return: 
    """
    try:
        source = get_command()
        file_name = get_run_file_name()
        page_source = driver.page_source
        match = re.search('清理|内存|存储空间|不足', page_source)
        if match:
            if messenger:
                messenger.send_message(f'{file_name}：内存空间不足, 匹配关键字【{match.group(0)}】',
                                       source=source)
                time.sleep(30)
            print('清内存...')
            if driver.__class__.__name__ == 'MyDriver':
                driver.driver.reset()
            elif driver.__class__.__name__ == 'WebDriver':
                driver.reset()
            time.sleep(3)
    except Exception as e:
        print(e.__repr__())


def get_all_package_names(serial):
    lines = os.popen(f'adb -s {serial} shell pm list packages').readlines()
    packages = set()
    for line in lines:
        packages.add(line.strip().split(':')[-1])
    return packages


def is_package_installed(package_name, serial=None):
    serial = serial or get_all_online_serials().pop()
    packages = get_all_package_names(serial)
    return package_name in packages


def get_manufacturer_name(serial):
    """获取手机厂商"""
    manufacturer_name = subprocess.check_output(f'adb -s {serial} -d shell getprop ro.product.brand'.split()).\
        decode('utf-8').strip()
    return manufacturer_name


def get_platform_version(serial):
    platform_version = subprocess.check_output(f'adb -s {serial} -d shell getprop ro.build.version.release'.split()).\
        decode('utf-8').strip()
    return platform_version


def get_free_storage_size(serial, manufacturer=None):
    if manufacturer is None:
        manufacturer = get_manufacturer_name(serial)
    if manufacturer == 'meizu':
        result = os.popen("""adb -s %s shell df /sdcard | grep /sdcard | awk '{print $4}'""" % serial).read().strip()
    else:
        result = os.popen("adb -s %s shell df /sdcard -h | grep storage | awk '{print $4}'" % serial).read().strip()
    if not re.match('\d', result):
        print(f'获取{serial}剩余存储空间大小失败！')
        return ''
    return result


def get_wechat_version(serial):
    """获取微信版本号"""
    line = os.popen(f'adb -s {serial} shell dumpsys package com.tencent.mm | grep versionName').read().strip()
    print(line)
    match = re.search('versionName=(\S+)', line)
    if match:
        return match.group(1)
    else:
        raise RuntimeError('获取微信版本号失败，请检查设备是否正常连接到电脑，是否安装了微信')


def get_package_version(package_name, serial):
    line = os.popen(f'adb -s {serial} shell dumpsys package {package_name} | grep versionName').read().strip()
    print(line)
    match = re.search('versionName=(\S+)', line)
    if match:
        return match.group(1)
    else:
        raise RuntimeError(f'获取{package_name}版本号失败，请检查设备是否正常连接到电脑，是否安装了{package_name}')


def get_all_online_serials():
    """获取所有连接到电脑的手机序列号"""
    lines = os.popen('adb devices | grep -v attached | grep device ').readlines()
    if lines:
        serials = set()
        for line in lines:
            serials.add(line.split('\t')[0])
        return serials


serial_imei_dict = {}


def get_imei_meizu_by_dialer(serial):
    """
    魅族手机：通过模拟拨号获取imei
    :param serial: 手机序列号
    :return: imei
    """
    global serial_imei_dict
    driver = init_driver(serial=serial, appPackage='com.android.dialer', appActivity='.DialtactsActivity')
    if '确定' in driver.page_source:
        driver.find_element_by_xpath('//android.widget.Button[@text="确定"]').click()
    driver.find_element_by_xpath('//android.widget.ImageButton[@resource-id="com.android.dialer:id/star"]').click()
    driver.find_element_by_xpath('//android.widget.ImageButton[@resource-id="com.android.dialer:id/pound"]').click()
    driver.find_element_by_xpath('//android.widget.ImageButton[@resource-id="com.android.dialer:id/zero"]').click()
    driver.find_element_by_xpath('//android.widget.ImageButton[@resource-id="com.android.dialer:id/six"]').click()
    driver.find_element_by_xpath('//android.widget.ImageButton[@resource-id="com.android.dialer:id/pound"]').click()
    imei_element = driver.find_element_by_xpath('//android.widget.TextView[@resource-id="android:id/message"]')
    imei_match = re.search('IMEI1:(\d+)', imei_element.text)
    if imei_match:
        imei = imei_match.group(1)
        serial_imei_dict[serial] = imei
        return imei
    else:
        print(f'{serial}: 获取imei失败')


def get_imei_meizu_from_cellphone_info(serial, max_tries=3):
    """
    魅族手机：通过模拟点击，设置-》关于手机, 页面有imei信息
    :param serial: 手机序列号
    :param max_tries: 
    :return: 
    """
    global serial_imei_dict
    for times in range(max_tries):
        driver = init_driver(serial=serial, appPackage='com.android.settings', appActivity='.Settings')
        driver.swipe(300, 1200, 300, 300, duration=200)
        driver.swipe(300, 1200, 300, 300, duration=200)
        time.sleep(3)
        driver.find_element_by_xpath('//*[@text="关于手机"]').click()
        imei_element = driver.find_element_by_xpath('//*[contains(@text,"IMEI1：")]')
        imei = imei_element.text.split('：')[-1]
        serial_imei_dict[serial] = imei
        return imei
    print(f'{serial}: 获取imei失败')


def get_imei_oneplus_by_dialer(serial):
    pass


def get_imei_by_adb_call(serial):
    """魅族、一加通用, 但是个别获取的是IMEI2的值，个别会获取不到"""
    result = os.popen(f'adb -s {serial} shell service call iphonesubinfo 1').read()
    numbers = re.findall('(\d)\.', result)
    if numbers:
        imei = ''.join(numbers)
        serial_imei_dict[serial] = imei
        return imei


def get_all_imeis(serials=None, func=get_imei_by_adb_call):
    serials = serials or get_all_online_serials()
    global serial_imei_dict
    print(serials)
    threads = []
    for serial in serials:
        t = Thread(target=func, args=(serial,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    pprint(serial_imei_dict)
    return serial_imei_dict


def wechat_get_id_and_nickname(serial, driver=None, raise_exception=False):
    """获取微信号和昵称"""
    MyDriver = __import__('appium_robot.robot.tools.my_driver_and_element', fromlist=['MyDriver']).MyDriver
    driver = driver or init_driver(serial, appPackage="com.tencent.mm", appActivity=".ui.LauncherUI")
    my_driver = MyDriver(driver, serial=serial, position_dict={})
    wechat_version = get_wechat_version(serial)
    xpath_object = XPATH_OBJECT_ALL_VERSIONS[wechat_version]
    try:
        wechat_id_element = my_driver.find_element_and_click(
            xpath_object.me_text, expect_element=xpath_object.get_wechat_id,
            raise_exception=False, max_retries=1)
        if not wechat_id_element:
            print('1'*100)
            wechat_id_element = my_driver.adb_tap(
                position=(630, 1230), expect_element=xpath_object.get_wechat_id)
        text = wechat_id_element.text
        print(text)
        wechat_id = text.split('：')[-1]
        nickname_element = my_driver.find_element_by_xpath(xpath_object.get_nickname)
        nickname = nickname_element.text
        print(f'昵称：{nickname}')
        return wechat_id, nickname
    except Exception as e:
        print(f'{serial}: 获取微信号和昵称失败！')
        print(e.__repr__())
        print_exc()
        if raise_exception:
            raise


def debug_wechat(serial):
    """功能：打开微信，进入ipdb调试模式"""
    from appium_robot.robot.tools.my_driver_and_element import MyDriver, MyElement
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from appium_robot.robot.wechat_work.setting import XPATH_DICT_ALL_VERSIONS, XPATH_OBJECT_ALL_VERSIONS
    driver = init_driver(serial=serial)
    wait = WebDriverWait(driver, 5)
    my_driver = MyDriver(driver, serial=serial, position_dict={})
    print(my_driver.__repr__())
    wechat_version = get_wechat_version(serial=serial)
    if wechat_version in XPATH_DICT_ALL_VERSIONS and wechat_version in XPATH_OBJECT_ALL_VERSIONS:
        xpath_dict = XPATH_DICT_ALL_VERSIONS[wechat_version]
        xpath_object = XPATH_OBJECT_ALL_VERSIONS[wechat_version]
        print('xpath_dict和xpath_object变量创建成功')
    print('微信版本：%s' % wechat_version)
    import ipdb
    ipdb.set_trace()


if __name__ == '__main__':
    """
    python3 -m appium_robot.robot.tools.appium_functools --serial 710MVBR723R3Y
    """
    show_module(form='*')
    _serial = get_valid_serial(sys.argv[2])
    debug_wechat(_serial)
