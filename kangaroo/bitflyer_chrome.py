import json
import time

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options

import chromedriver_binary

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')  # Last I checked this was necessary.

url = 'https://lightning.bitflyer.jp/'
user = 'guo.xiaoyong@gmail.com'
passwd = '51e1351157d9dbcb2cde54fcdae2744d'

caps = DesiredCapabilities.CHROME
caps['loggingPrefs'] = {'performance': 'ALL'}
driver = webdriver.Chrome('chromedriver', chrome_options=options, desired_capabilities=caps)
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


def get_websocket_msg():
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
    fetched_timestamp = int(time.time() * 10**6) * 1000
    try:
      message_str = entry['message']
      print(message_str)
      message = json.loads(message_str)
      timestamp = message['message']["params"]["timestamp"]
      method = message['message']["method"]
      if method.lower() == "Network.webSocketFrameReceived".lower():
        payload_str = message['message']['params']['response']['payloadData']
    except KeyError as e:
      #print("KeyError", e, entry)
      pass
  return n


try:
  while True:
    get_websocket_msg()
except KeyboardInterrupt:
  print(driver.page_source())

driver.close()
