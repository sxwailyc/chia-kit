#!/usr/bin/python
# -*- coding: utf-8 -*-

import psutil


def get_cpu_model():
    with open('/proc/cpuinfo') as fd:
        for line in fd:
            if line.startswith('model name'):
                cpu_model = line.split(':')[1].strip().split()
                cpu_model = cpu_model[0] + ' ' + cpu_model[2] + ' ' + cpu_model[-1]
                return cpu_model
    return 'unknow'


def get_temperature():
    cpu_model = get_cpu_model()
    print(cpu_model)
    temperatures = psutil.sensors_temperatures()
    for key, items in temperatures.items():
        print(key)
        #print(items, type(items))
        for item in items:
            print(item, type(item))


if __name__ == '__main__':
    print(get_temperature())