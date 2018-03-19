import json
import time
import atexit

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

import chromedriver_binary

from cffi import FFI

ffi = FFI()

ffi.cdef('long get_timestamp();')

_time = ffi.verify('''
#include <sys/time.h>

long get_timestamp() {
  struct timeval tv;
  gettimeofday(&tv, NULL);  // Ignore return code.
  return tv.tv_sec * 1000000000LL + tv.tv_usec * 1000LL;
}
''')

get_timestamp = _time.get_timestamp

def parse_message(message):
  msg = json.loads(message)
  fetch_time = msg['fetch_time']

def create_driver():
  options = Options()
  options.add_argument('--headless')
  options.add_argument('--disable-gpu')  # Last I checked this was necessary.
  options.add_argument('--mute-audio')

  url = 'https://lightning.bitflyer.jp/'
  user = 'guo.xiaoyong@gmail.com'
  passwd = '51e1351157d9dbcb2cde54fcdae2744d'
  caps = DesiredCapabilities.CHROME
  caps['loggingPrefs'] = {'performance': 'ALL'}
  driver = webdriver.Chrome(
      'chromedriver', chrome_options=options, desired_capabilities=caps)
  driver.implicitly_wait(30)
  driver.get(url)
  username_input = driver.find_element_by_id('LoginId')
  password_input = driver.find_element_by_id('Password')
  login_button = driver.find_element_by_id('login_btn')
  username_input.clear()
  username_input.send_keys(user)
  password_input.clear()
  password_input.send_keys(passwd)
  login_button.click()
  return driver


def get_websocket_msg(driver):
  n = 0
  x = None
  try:
    x = driver.get_log("performance")
  except OSError as e:
    # OSError: [Errno 99] Cannot assign requested address
    pass
  if x is None:
    return n

  for entry in x:
    try:
      message_str = entry['message']
      message = json.loads(message_str)
      timestamp = message['message']["params"]["timestamp"]
      method = message['message']["method"]
      if method.lower() == "Network.webSocketFrameReceived".lower():
        payload_str = message['message']['params']['response']['payloadData']
        payload = json.loads(payload_str)
        payload['fetch_time'] = get_timestamp()
        res = json.dumps(payload)
        print(res)

    except KeyError as e:
      #print("KeyError", e, entry)
      pass
  return n


driver = create_driver()
try:
  while True:
    get_websocket_msg(driver)
except KeyboardInterrupt:
  print(driver.page_source())

driver.close()
