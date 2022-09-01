#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import os
import time
from datetime import datetime


def log(msg):
    s = "[%s]%s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(s)


def is_matcher(name, suffixs):
    modify_time = os.path.getmtime(name)
    time_diff = time.time() - modify_time
    if time_diff < 5 * 60:
        # not return the file when it was updating
        return False
    for suffix in suffixs:
        if name.endswith(".%s" % suffix):
            return True
    return False


def _get_tree_files(_dir, suffixs=[]):
    if dir and os.path.isdir(_dir):
        walker = os.walk(_dir)
        for item in walker:
            for fileName in item[2]:
                filePath = os.path.join(item[0], fileName)
                if os.path.isfile(filePath):
                    yield filePath


def _get_files(_dir, suffixs=[]):
    if not _dir or not os.path.isdir(_dir):
        return []
    names = os.listdir(_dir)
    files = []
    for name in names:
        name = os.path.join(_dir, name)
        if os.path.isfile(name) and is_matcher(name, suffixs):
            files.append(name)
    return files


def get_files(_dir, suffixs=[], recursion=False):
    if recursion:
        return _get_tree_files(_dir, suffixs)
    else:
        return _get_files(_dir, suffixs)


def get_file_size(file_path):
    size = os.path.getsize(file_path)
    size = size / float(1024 * 1024 * 1024)
    return round(size, 2)


class PlotCleaner:
    BAD_PLOT = "bad_plot"
    DUPLICATE_PLOT = "duplicate_plot"

    def __init__(self, action, plot_dir_list, recursion=True, suffixs=['plot', 'tmp'], plot_min_size=101,
                 delete=False):
        self.action = action
        self.plot_dir_list = plot_dir_list
        self.recursion = recursion
        self.suffixs = suffixs
        self.plot_min_size = plot_min_size
        self.delete = delete

    def start(self):
        if self.action == PlotCleaner.BAD_PLOT:
            self.find_bad_plot()
        elif self.action == PlotCleaner.DUPLICATE_PLOT:
            self.find_duplicate_plot()
        else:
            log("unknow action:%s" % self.action)

    def find_duplicate_plot(self):
        ids = {}
        duplicate_ids = {}
        for dir_name in self.plot_dir_list:
            if os.path.exists(dir_name):
                files = get_files(dir_name, ['plot'], self.recursion)
                for filename in files:
                    _id = filename.replace(".plot", "").split("-")[-1]
                    if _id in ids:
                        duplicate_files = duplicate_ids.get(_id, [])
                        if not duplicate_files:
                            duplicate_files.append(ids[_id])
                        duplicate_files.append(filename)
                        duplicate_ids[_id] = duplicate_files
                    else:
                        ids[_id] = filename

        for k, v in duplicate_ids.items():
            log("duplicate plot,id[%s], files%s" % (k, v))

    def find_bad_plot(self):
        bad_plots = {}
        for dir_name in self.plot_dir_list:
            if os.path.exists(dir_name):
                files = get_files(dir_name, self.suffixs, self.recursion)
                for filename in files:
                    size = get_file_size(filename)
                    if size < self.plot_min_size:
                        bad_plots[filename] = size

        print("find %s bad plot files." % len(bad_plots))
        for k, v in bad_plots.items():
            print("%s -> %sGB" % (k, v))
            if self.delete:
                os.remove(k)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="""
           This script is for find bad plots or duplicate plot.
        """)
    parser.add_argument("action", help="bad_plot: find bad plots; duplicate_plot: find duplicate plots ",
                        choices=['bad_plot', 'duplicate_plot'])
    parser.add_argument("plot_dir_list", help="chia plot dir list, split by comma")
    parser.add_argument("-r", "--recursion", action="store_true", help="recursion find plots, default is False",
                        default=False)
    parser.add_argument("-d", "--delete", action="store_true",
                        help="whether perform a delete operation when find a bad plot file, default is Flase",
                        default=False)
    parser.add_argument("-s", "--suffixs", metavar="",
                        help="handle file suffix list, plit by comma. default is plot,tmp", default='plot,tmp')
    parser.add_argument("-m", "--plot-min-size", metavar="", type=int,
                        help="plot file min size, less than this value be considered for bad plot, default is 101Gb",
                        default=101)

    args = parser.parse_args()

    action = args.action
    plot_dir_list = args.plot_dir_list.split(",")
    recursion = args.recursion
    delete = args.delete
    suffixs = args.suffixs.split(",")
    plot_min_size = args.plot_min_size
    cleaner = PlotCleaner(action, plot_dir_list, recursion, suffixs, plot_min_size, delete)
    cleaner.start()
