#!/bin/sh

# Database info
DB_USER="root"
DB_PASS="XXXXXX"
DB_HOST="localhost"
DB_NAME="fortest"

# Others vars
BIN_DIR="/usr/bin"            #the mysql bin path
BCK_DIR="/srv/awesome/backup"    #the backup file directory
DATE=`date +%Y%m%d`

# TODO
# /usr/bin/mysqldump --opt -ubatsing -pbatsingpw -hlocalhost timepusher > /mnt/mysqlBackup/db_`date +%F`.sql
$BIN_DIR/mysqldump --opt -u$DB_USER -p$DB_PASS -h$DB_HOST $DB_NAME > $BCK_DIR/test_$DATE.sql

#还原数据库
#用mysql-front导入前一天的 *.sql 文件即可恢复数据