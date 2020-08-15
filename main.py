# coding: UTF-8

import sys
import time
import dht11
import subprocess
import RPi.GPIO as GPIO
from datetime import datetime
import requests

# out pin
out_pin = 4

# + pin
power_pin = 16

max_try = 300

slack_url = None

csv_path = None


def power_on():
    GPIO.output(power_pin, GPIO.LOW)
    time.sleep(6)
    GPIO.output(power_pin, GPIO.HIGH)
    time.sleep(1)


def power_off():
    GPIO.output(power_pin, GPIO.LOW)


def get_data():
    instance = dht11.DHT11(pin=out_pin)
    result = instance.read()
    return result.temperature, result.humidity


# time , try_num , temperature , humidity , cpu_temp
def print_csv(try_num, temperature, humidity, cpu_temp):
    t = time.time()
    p = datetime.fromtimestamp(t)
    if temperature == 0 and humidity == 0:
        # Failed to get values.
        print(f"{p} , {try_num} , , , {cpu_temp}")
    else:
        print(f"{p} , {try_num} , {temperature} , {humidity} , {cpu_temp}")


def get_cpu_temp():
    with open("/sys/class/thermal/thermal_zone0/temp","r") as f:
        result=int(f.readline())
        return result / 1000


def send_to_slack(text):
    global slack_url
    if slack_url is not None:
        resp = requests.post(slack_url,
                             data={"payload": {"text": text}.__str__()})
        return resp.status_code == 200
    return True


def is_last_success():
    global csv_path
    with open(csv_path, "r") as f:
        data = f.readlines()
        return data[len(data) - 1].find(f", {max_try} ,") == -1


def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(power_pin, GPIO.OUT)
    try:
        power_on()
        i = 0
        for i in range(max_try + 1):
            if i % 50 == 0:
                # Reboot DHT11 every 50 times.
                power_on()
            temperature, humidity = get_data()
            cpu_temp = get_cpu_temp()

            if temperature == 0 and humidity == 0:
                # Retry
                continue
            if not is_last_success():
                send_to_slack("Recovered from failure")
            print_csv(i, temperature, humidity, cpu_temp)
            power_off()
            GPIO.cleanup()
            return

        cpu_temp = get_cpu_temp()
        # Failed to get data.
        if is_last_success():
            send_to_slack("Failed to get data from DHT11")
        print_csv(i, 0, 0, cpu_temp)
        power_off()
        GPIO.cleanup()
    except:
        pass


def usage():
    print("sudo python3 main.py [csv path] [slack webhook url]")
    exit(0)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "-h":
            usage()
        csv_path = sys.argv[1]
    if len(sys.argv) > 2:
        slack_url = sys.argv[2]
    main()
