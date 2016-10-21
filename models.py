#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Models for user, blog, comment.
'''

__author__ = 'Michael Liao'

import time, uuid

from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):                                          #定义出用户模块
    __table__ = 'users'                                     #表名是：user

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')      #id设置成主键
    email = StringField(ddl='varchar(50)')                  #读入email
    passwd = StringField(ddl='varchar(50)')                 #读入密码
    admin = BooleanField()                                  #读入管理员身份，数据类型是布尔型
    name = StringField(ddl='varchar(50)')                   #名字
    image = StringField(ddl='varchar(500)')                 #头像照片
    created_at = FloatField(default=time.time)              #创建时间缺省值

class Blog(Model):                                          #定义出博客模块
    __table__ = 'blogs'                                     #表名是：blogs

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')      #id设置成主键，id默认值为next_id
                                                            #   id是类的属性，不是实例的属性。下同。不用初始化
    user_id = StringField(ddl='varchar(50)')                #记录出用户的id
    user_name = StringField(ddl='varchar(50)')              #记录出用户的名字
    user_image = StringField(ddl='varchar(500)')            #记录出用户的照片
    name = StringField(ddl='varchar(50)')                   #博客的名字
    summary = StringField(ddl='varchar(200)')               #博客摘要
    content = TextField()                                   #博客主体内容
    created_at = FloatField(default=time.time)              #创建时间缺省值

class Comment(Model):                                       #定义出评论模块
    __table__ = 'comments'                                  #表名是：comments

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')      #id设成主键
    blog_id = StringField(ddl='varchar(50)')                #博客的id
    user_id = StringField(ddl='varchar(50)')                #评论用户的id
    user_name = StringField(ddl='varchar(50)')              #用户的名字
    user_image = StringField(ddl='varchar(500)')            #用户的照片
    content = TextField()                                   #评论的内容
    created_at = FloatField(default=time.time)              #创建时间缺省值
