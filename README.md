### 奇亚P盘中用到的一些小工具，做一下归纳

#### 1. move_assistant.py 从临时盘往机械盘转移文件的一个脚本

##### 1.1 使用方法

```commandline
python3 move_assistant.py 临时目录  机械盘1,机械盘2,机构盘3.....
```

###### 完整参数列表

```commandline
usage: move_assistant.py [-h] [--max-concurrency] [--sub-dir-name] [--scan-interval] [--minimal-space] [--move-strategy] temp_dir hdd_dir_list

This script is for move plot files from ssd to hdd.

positional arguments:
  temp_dir            chia plot temp dir
  hdd_dir_list        chia hdd dir list, split by comma

optional arguments:
  -h, --help          show this help message and exit
  --max-concurrency   max concurrency, default is 5 //最大并发数
  --sub-dir-name      sub dir name, default is empty //子目录，默为空,空则不创建子目录
  --scan-interval     scan interval, default is 30 seconds //扫盘间隔
  --minimal-space     minimal space need, default is 103GB  //移图最小需要空间,改小了空间不够会报错
  --move-strategy     move strategy 1. by order 2. avg, default is 1 //移动策略 1. 目录顺序移动, 前面的盘会最先塞满 2. 优先移到剩余空间最大的盘,所有盘会平均分配
```

###### 