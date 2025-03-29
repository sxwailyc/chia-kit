#!/bin/bash

# 批量测试机械硬盘读取速度脚本（修正速度计算）
# 使用方式：sudo ./test_hdd_speed.sh

# 检查是否以root运行
if [[ $EUID -ne 0 ]]; then
   echo "错误：此脚本必须以root权限运行 (使用sudo)" 
   exit 1
fi

# 配置参数
BS=1M          # 块大小 (1MB)
COUNT=1000     # 块数量 (总数据量 = 1M*1000 = 1000MB)
OUTPUT="/dev/null"

# 获取所有机械硬盘设备列表
get_mechanical_disks() {
  mechanical_disks=()
  for device in /dev/sd*; do
    # 排除分区（只处理整个磁盘）
    if [[ $device =~ [0-9]$ ]]; then continue; fi

    device_name=$(basename "$device")
    rotational_path="/sys/block/$device_name/queue/rotational"
    
    # 检查是否为机械硬盘
    if [[ -f $rotational_path ]]; then
      rotational=$(cat "$rotational_path")
      if [[ $rotational -eq 1 ]]; then
        mechanical_disks+=("$device")
      fi
    fi
  done

  if [[ ${#mechanical_disks[@]} -eq 0 ]]; then
    echo "未找到机械硬盘！"
    exit 1
  fi
}

# 测试单个硬盘速度并计算MB/s
test_disk_speed() {
  local device=$1
  echo -e "\n正在测试设备: $device"

  # 运行DD命令并捕获时间
  echo "-------------------------------------"
  output=$( { time dd if=$device of=$OUTPUT bs=$BS count=$COUNT iflag=direct status=none; } 2>&1 )
  echo "$output"
  echo "-------------------------------------"

  # 解析时间计算速度
  real_time=$(grep real <<< "$output" | awk '{print $2}')
  
  # 将时间转换为秒（处理0m5.23s格式）
  mins=$(cut -d'm' -f1 <<< "$real_time")
  secs=$(cut -d'm' -f2 <<< "$real_time" | tr -d 's')
  total_secs=$(echo "$mins*60 + $secs" | bc -l)

  # 正确计算速度（总数据量MB / 时间秒）
  total_mb=$(echo "$COUNT" | bc)  # 因为BS=1M，COUNT=1000 → 1000MB
  speed=$(echo "scale=2; $total_mb / $total_secs" | bc -l)
  
  echo "平均速度: ${speed}MB/s"
}

# 主流程
main() {
  mechanical_disks=()
  get_mechanical_disks

  echo "检测到机械硬盘列表:"
  printf "  %s\n" "${mechanical_disks[@]}"
  echo -e "\n开始测试读取速度 (块大小: $BS, 块数量: $COUNT)..."

  for disk in "${mechanical_disks[@]}"; do
    test_disk_speed "$disk"
  done
}

main
