# Author: Guo Xiaoyong

import time

import pyautogui

import util
import homework


def send_message(message):
    pyautogui.typewrite(message)
    pyautogui.press('enter')


def main():
    prev_calendar = util.retrieve_managebac_calendar()
    while True:
        time.sleep(600)
        now_calendar = util.retrieve_managebac_calendar()
        if now_calendar != prev_calendar:
            continue
        text = homework.get_latest_homework()
        send_message(text)


if __name__ == '__main__':
    pyautogui.FAILSAFE = True
    time.sleep(20)  # Prepare GUI
    main()
