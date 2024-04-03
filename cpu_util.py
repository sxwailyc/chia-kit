#!/usr/bin/python
# -*- coding: utf-8 -*-

import psutil


def get_cpu_model():
    with open('/proc/cpuinfo') as fd:
        for line in fd:
            if line.startswith('model name'):
                cpu_model = line.split(':')[1].strip()
                return cpu_model
    return 'unknow'


def get_cpu_temperature_key(cpu_model):
    if cpu_model.startswith("Intel(R) Xeon(R)"):
        return 'coretemp', 'Package id 0'
    if cpu_model.startswith("AMD"):
        return 'k10temp', 'Tctl'

    return None, None


def get_temperature():
    cpu_model = get_cpu_model()
    print(cpu_model)
    top_key, second_key = get_cpu_temperature_key(cpu_model)
    temperatures = psutil.sensors_temperatures()
    print(top_key, second_key)
    for key, items in temperatures.items():
        if key != top_key:
            continue

        for item in items:
            print(item.label)
            if item.label == second_key:
                return item.current

    return 0


if __name__ == '__main__':
    print(get_temperature())