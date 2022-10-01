### 奇亚P盘中用到的一些小工具，做一下归纳

#### 1. move_assistant.py 从临时盘往机械盘转移文件的一个脚本

##### 1.1 使用方法

```commandline
python3 move_assistant.py 临时目录  机械盘1,机械盘2,机械盘3.....
```

##### 1.2 完整参数列表

```commandline
usage: move_assistant.py [-h] [--max-concurrency] [--sub-dir-name] [--scan-interval] [--minimal-space] [--move-strategy] temp_dir_list hdd_dir_list

This script is for move plot files from ssd to hdd.

positional arguments:
  temp_dir_list       chia plot temp dir list, split by comma #临时盘目录列表，逗号分隔,  
  hdd_dir_list        chia hdd dir list, split by comma #机械盘目录列表，逗号分隔,  /mnt/chia01,/mnt/chia02, 可以指定该目录最大存放文件数，比如 /mnt/chia01=147,/mnt/chia02=128

optional arguments:
  -h, --help          show this help message and exit
  --max-concurrency   max concurrency, default is 5 //最大并发数
  --sub-dir-name      sub dir name, default is empty //子目录，默为空,空则不创建子目录
  --scan-interval     scan interval, default is 30 seconds //扫盘间隔
  --minimal-space     minimal space need, default is 103GB  //移图最小需要空间,改小了空间不够会报错
  --move-strategy     move strategy 1. by order 2. avg, default is 1 //移动策略 1. 目录顺序移动, 前面的盘会最先塞满 2. 优先移到剩余空间最大的盘,所有盘会平均分配
```

#### 2. plot_cleaner.py  清理一些坏的plot文件，临时文件，以及重复的plot文件的脚本

##### 2.1 使用方法
```commandline
python3 plot_cleaner.py 动作 目录
```

##### 2.2 完整参数列表

```commandline
usage: plot_cleaner.py [-h] [-r] [-d] [-s] [-m] {bad_plot,duplicate_plot} plot_dir_list

This script is for find bad plots or duplicate plot.

positional arguments:
  {bad_plot,duplicate_plot}
                        bad_plot: find bad plots; duplicate_plot: find duplicate plots #执行的动作 bad_plot 找出不合法的图 duplicate_plot 找出重复的图
  plot_dir_list         chia plot dir list, split by comma  #目录列表,逗号分隔

options:
  -h, --help            show this help message and exit  
  -r, --recursion       recursion find plots, default is False  //是否递归查找文件
  -d, --delete          whether perform a delete operation when find a bad plot file, default is Flase //是否执行删除动作
  -s , --suffixs        handle file suffix list, plit by comma. default is plot,tmp //处理的文件后缀类型
  -m , --plot-min-size 
                        plot file min size, less than this value be considered for bad plot, default is 101Gb //plot 文件大小最小值，小于该值认为是不合法的plot文件
```

#### 3. disk_util.py  自动挂载硬盘

##### 3.1 使用方法
```commandline
python3 disk_util.py 动作
```

##### 3.2 完整参数列表

```commandline
usage: disk_util.py [-h] [-d DIR] [-p PREFIX] [-e] {mount,mkfs}

This script is mount disk or make file system.

positional arguments:
  {mount,mkfs}          mount: mount disk; mkfs: make file system

optional arguments:
  -h, --help            show this help message and exit
  -d DIR, --dir DIR     mount dir, defautl is /mnt/  //挂载目录，默认为 /mnt/
  -p PREFIX, --prefix PREFIX        //目录前缀，默认为空，比如可以为 chia, 则挂载目录依次为 /mnt/chia01 /mnt/chia02
                        mount sub foler preifx, default is empty
  -e, --execute         whether perform operation, default is Flase   //是否执行，默认为否，只会输出挂载命令
```
