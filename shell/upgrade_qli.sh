#!/bin/sh

mkdir -p /data/app/qli-app
cd /data/app/qli-app
rm -f /data/app/qli-app/*

wget -O qli.tar.gz $1

tar zxvf qli.tar.gz

supervisorctl stop qli

rm -f /data/app/qli/qli-Client
rm -f /data/app/qli/qli-runner
rm -f /data/app/qli/qli-runner.lock
rm -rf /data/app/qli/tmp
rm -rf /data/app/qli/log

cp /data/app/qli-app/qli-Client /data/app/qli/

supervisorctl start qli

tail -f /data/log/qli.out.log
 
