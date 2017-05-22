#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Default configurations.
'''

__author__ = 'hellozmz'

configs = {
    'debug': True,
    'db': {
        'host': '127.0.0.1',    #主机ip   开发环境
        'port': 3306,
        'user': 'root',         #www    改成了自己的账号密码
        'password': '123456',   #www
        'db': 'awesome'
    },
    'session': {
        'secret': 'XXXXXXX'
    }
}
