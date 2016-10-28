#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

import asyncio, logging

import aiomysql

def log(sql, args=()):                                                  #打印日志的函数
    logging.info('SQL: %s' % sql)

@asyncio.coroutine
def create_pool(loop, **kw):                                            #增加一个全局连接池
                                                                        #   有了连接池，尽量做到了复用。
                                                                        #   减少不断打开数据库的问题
    logging.info('create database connection pool...')
    global __pool                                                       #调用的异步的mysql的创建连接池的函数
    __pool = yield from aiomysql.create_pool(                           #在这个池中加入各个值，并且一个初始化
        host=kw.get('host', 'localhost'),                               #主机  kw.get可以直接将数据捆绑起来
        port=kw.get('port', 3306),                                      #端口  没有get 的应该不可以
        user=kw['user'],                                                #用户名
        password=kw['password'],                                        #密码
        db=kw['db'],                                                    #数据库的名字
        charset=kw.get('charset', 'utf8'),                              #编码方式
        autocommit=kw.get('autocommit', True),                          #设置自动提交的方式
        maxsize=kw.get('maxsize', 10),                                  #最大量
        minsize=kw.get('minsize', 1),                                   #最小量
        loop=loop                                                       #循环
                                                                        #说一下get(a,b)，python自带的函数，返回
                                                                        #   字典中名字a的项，如果没有返回b值
    )

@asyncio.coroutine
def select(sql, args, size=None):                                       #执行select语句，查找
    log(sql, args)                                                      #打印出来功能日志
    global __pool
    with (yield from __pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)               #打开游标
        yield from cur.execute(sql.replace('?', '%s'), args or ())      #SQL语句的占位符和Mysql的不一样
                                                                        #SQL:?  Mysql:%s
                                                                        #其实加入了库，这些函数都是有的，自己
                                                                        #   只需要加入参数就好->括号中的都是
        if size:                                                        #主要的部分应该是在这里
            rs = yield from cur.fetchmany(size)                         #根据不同情况，提取不同匹配项
        else:                                                           #匹配指定数目的，具体根据size看
            rs = yield from cur.fetchall()                              #匹配所有的
        yield from cur.close()                                          #关闭数据库游标
        logging.info('rows returned: %s' % len(rs))                     #打印出日志
        return rs                                                       #返回匹配的项。fetchmany是库中的

@asyncio.coroutine
def execute(sql, args, autocommit=True):                                #执行各种操作：插入，修改，删除
    log(sql)                                                            #可以看出来，查询和其他的操作传参数有区别
    with (yield from __pool) as conn:                                   #   查询时需要知道查询的个数
        if not autocommit:                                              #INSERT、UPDATE、DELETE操作
            yield from conn.begin()
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?', '%s'), args)        #替换占位符
            affected = cur.rowcount                                     #获取结果集的行数
            yield from cur.close()
            if not autocommit:
                yield from conn.commit()                                #开始执行任务
        except BaseException as e:
            if not autocommit:
                yield from conn.rollback()                              #如果出现问题了，及时回滚
            raise
        return affected                                                 #返回整数，表示处理的行数

#注意区分select和其他几个操作Insert等区别：execute()函数和select()函数所不同的是，cursor对象不返回结果集，
#   而是通过rowcount返回结果数。===>select()返回结果，其他操作返回行数。工作的主体是select

def create_args_string(num):                                            #把参数的个数替换成'?'的字符串
    L = []                                                              #   传入的就是数字，每个元素后加入？后，用，隔开
    for n in range(num):                                                #for: num = 5, range(num)=[0,1,2,3,4]
        L.append('?')                                                   #L = ['?','?','?','?','?']
    return ', '.join(L)                                                 #'?, ?, ?, ?, ?' ->结果是一个字符串

class Field(object):                                                    #先定义一个基本的基类，为了接下来的。field子类
                                                                        #   不同类型的数据的定义做一个基类
                                                                        #   返回索引。主要是用来查询的
                                                                        #   属性的基类   
    def __init__(self, name, column_type, primary_key, default):        #初始化：名字，列，主键，默认值
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):                                                  #返回几个值，类的名字，列的类型，名字
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):                                               #字符串形式的查询

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'): 
                                                                        #DDL(Data Definition Language) 
                                                                        #   数据库定义语言，包括：
                                                                        #   CREATE,ALTER,DROP,TRUNCATE,
                                                                        #   COMMENT,RENAME
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):                                              #真假形式的查询

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):                                              #整形的查询

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):                                                #浮点数形式的查询

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):                                                 #文字形式的查询

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

class ModelMetaclass(type):                                             #模型层的基类

    def __new__(cls, name, bases, attrs):                               #新建一个属性
        if name=='Model':
            return type.__new__(cls, name, bases, attrs)
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        mappings = dict()                                               #map映射是一个字典，元组
        fields = []                                                     #列表
        primaryKey = None                                               #未设置主键
        for k, v in attrs.items():                                      #在属性中查找k值
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v                                         #在映射的字典中，将k和v匹配起来
                if v.primary_key:
                    # 找到主键:
                    if primaryKey:
                        raise StandardError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)                                #在结尾添加k的值
        if not primaryKey:
            raise StandardError('Primary key not found.')
        for k in mappings.keys():                                   #把所有的映射中的k值都吐出来
            attrs.pop(k)                                            #清空了属性的列表
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))    #`:英文输入法时，Esc下边。数据库中`data`和自带的data区分
                                                                    #   map(f = field),将field数据转到了f中。相当于做tmp
        attrs['__mappings__'] = mappings # 保存属性和列的映射关系      自己定义了一堆属性
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey # 主键属性名
        attrs['__fields__'] = fields # 除主键外的属性名
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
                                                                    #查找     __select__ python自有变量&私有变量
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
                                                                    #增加
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
                                                                    #修改
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
                                                                    #删除
        return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass=ModelMetaclass):                            #定义一个模型层的类！

    def __init__(self, **kw):                                           #初始化
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):                                         #针对x.y形式的查询
        try:
            return self[key]                                            #对于存在key的返回值，不存在的返回错误
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):                                  #针对x.y形式的保存
        self[key] = value

    def getValue(self, key):                                            #得到属性值
        return getattr(self, key, None)

    def getValueOrDefault(self, key):                                   #得到属性默认值
        value = getattr(self, key, None)
        if value is None:                                               #默认的时候要怎么得到值
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value

    @classmethod
    @asyncio.coroutine
    def findAll(cls, where=None, args=None, **kw):                      #查找
        ' find objects by where clause. '
        sql = [cls.__select__]                                          #在142行处有具体的话
        if where:                                                       #选择查找的条件
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:                                                     #选择输出的排序方式
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = yield from select(' '.join(sql), args)
        return [cls(**r) for r in rs]                                   #返回所有符合条件的值

    @classmethod                                                        #类方法
    @asyncio.coroutine                                                  #启用并发式
    def findNumber(cls, selectField, where=None, args=None):            #查找
        ' find number by select and where. '                            #select ? from ? where ?
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:                                                       #如果有where的条件，就在末尾加入。没有就算了
            sql.append('where')
            sql.append(where)
        rs = yield from select(' '.join(sql), args, 1)                  #调用本文件中的select函数
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    @classmethod                                                        #接下来的cls代表的可就是前边的Model了
    @asyncio.coroutine
    def find(cls, pk):                                                  #查找
        ' find object by primary key. '                                 #通过主键来找内容
        rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
                                                                        #在数据库中查找，pk保存主键值，也就是id,匹配1项
                                                                        #所以才会有调用__select__，__primary_key__情况
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    @asyncio.coroutine
    def save(self):                                                     #增加
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    @asyncio.coroutine
    def update(self):                                                   #修改
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = yield from execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    @asyncio.coroutine
    def remove(self):                                                   #删除
        args = [self.getValue(self.__primary_key__)]
        rows = yield from execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)
