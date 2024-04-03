#!/usr/bin/python
# -*- coding: utf-8 -*-

import psutil


def get_temperature():
    temperatures = psutil.sensors_temperatures()
    for key, item in temperatures.items():
        print(key)
        print(item, type(item))


if __name__ == '__main__':
    print(get_temperature())