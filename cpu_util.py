#!/usr/bin/python
# -*- coding: utf-8 -*-

import psutil


def get_temperature():
    temperatures = psutil.sensors_temperatures()
    for key, items in temperatures.items():
        print(key)
        #print(items, type(items))
        for item in items:
            print(item, type(item))


if __name__ == '__main__':
    print(get_temperature())