#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'hellozmz'

import asyncio, logging

import aiomysql

def log(sql, args=()):                                                  #打印日志的函数
    logging.info('SQL: %s' % sql)

'''
创建数据库连接池，主要的变量为登录数据库的用户名，密码，还有数据的格式等设置条件
'''
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
                                                                        #**kw中包含的是config_default.py中内容
    )
'''
将select操作实现出来，使用的时候直接使用select函数，就相当于直接操作数据库一样。相当于一个翻译，转化成数据库可使用的语言
'''
@asyncio.coroutine
def select(sql, args, size=None):                                       #执行select语句，查找
    log(sql, args)                                                      #打印出来功能日志
    global __pool
    with (yield from __pool) as conn:                                   #在连接的库中，新建一条连接
        cur = yield from conn.cursor(aiomysql.DictCursor)               #打开游标
        yield from cur.execute(sql.replace('?', '%s'), args or ())      #SQL语句的占位符和Mysql的不一样
                                                                        #SQL:?  Mysql:%s
                                                                        #其实加入了库，这些函数都是有的，自己
                                                                        #   只需要加入参数就好->括号中的都是
        if size:                                                        #主要的部分应该是在这里
            rs = yield from cur.fetchmany(size)                         #根据不同情况，提取不同匹配项
        else:                                                           #匹配指定数目的，具体根据size看
            rs = yield from cur.fetchall()                              #匹配所有的，默认
        yield from cur.close()                                          #关闭数据库游标
        logging.info('rows returned: %s' % len(rs))                     #打印出日志
        return rs                                                       #返回匹配的项。fetchmany是库中的

def select_like(sql, args, size=None):                                       #执行like语句
    log(sql, args)
    global __pool
    with (yield from __pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace('?', '%s'), args or ())
        if size:
            rs = yield from cur.fetchmany(size)
        else:
            rs = yield from cur.fetchall()
        yield from cur.close()
        logging.info('rows returned: %s' % len(rs))
        return rs


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
        return affected                                                 #返回整数，表示需要处理的行数

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
        self.name = name                                                #通过看返回值可以发现，name是（对象）的名字
        self.column_type = column_type                                  #记录在mysql表中的数据类型
        self.primary_key = primary_key                                  #记录是否位主键
        self.default = default                                          #记录默认值

                                                                        #下面主要用来测试使用
    def __str__(self):                                                  #返回几个值，类的名字，列的类型，名字
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)
                                                                        #依次是类的名字
                                                                        #   类的属性，记录数据类型
                                                                        #   对象的名字

class StringField(Field):                                               #字符串形式的查询

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'): 
                                                                        #DDL(Data Definition Language) 
                                                                        #   数据库定义语言，包括：
                                                                        #   CREATE,ALTER,DROP,TRUNCATE,
                                                                        #   COMMENT,RENAME
                                                                        #本例子中，ddl对应的是column_type
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):                                              #真假形式的查询

    def __init__(self, name=None, default=False):                       #在class中的函数必须要有self，
                                                                        #   相当于一个定义
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

#Model只是一个基类，如何读出它的子类的映射信息，比如说User的映射信息，就需要meta class
#这样继承自Model的子类User等就可以扫描出来，并且存储到类属性中，如__table__,__mappings__等
#这个厉害，能够把所有的信息提取出来，留给继承自它的类使用继承自它的函数可以根据独到的内容去实现构造的函数
#扫描映射关系，把结果存到自己的属性中

class ModelMetaclass(type):                                             #模型层的基类
                                                                        #功能是要读取映射信息

    def __new__(cls, name, bases, attrs):                               #新建一个属性
                                                                        #   __new__参数要有cls,另外
                                                                        #   功能是提取当前类的参数，
                                                                        #   cls代表着这个类ModelMetaclass
                                                                        #   并且他还会先于__init__运行
                                                                        #   绑定的是类的对象，不是实例对象
        if name=='Model':                                               #排除Model类本身
            return type.__new__(cls, name, bases, attrs)                #传进来的参数全都返回了
        tableName = attrs.get('__table__', None) or name                #可以得到table表的名字，attr,name是传入的
                                                                        #__table__是在models.py中存在的
                                                                        #   不清粗的东西都是有来源的，往回找
        logging.info('found model: %s (table: %s)' % (name, tableName))
        mappings = dict()                                               #map映射是一个字典，元组
                                                                        #   获取所有的Field和主键
        fields = []                                                     #存放属性的列表
                                                                        #列表
                                                                        #   列表=可调整数组，
                                                                        #   元组=初始化后不可调整数组=>代码更加安全
        primaryKey = None                                               #未设置主键
                                                                        #接下来的部分厉害了，自己开始读取自己所有属性
                                                                        #   这就是连自己都不放过的表现啊
        for k, v in attrs.items():                                      #在属性中查找k值
                                                                        #   属性是什么呢？就是类中定义的内容
                                                                        #   每一项！！定义的各个变量
                                                                        #属性变量包括两部分：名字+存储格式
            if isinstance(v, Field):                                    #返回一个Field类型的东西，
                                                                        #   或者递归滴包含Field也可以
                logging.info('  found mapping: %s ==> %s' % (k, v))     #k=关键字，v=值
                                                                        #k是属性，v是值
                mappings[k] = v                                         #在映射的字典中，将k和v匹配起来
                if v.primary_key:                                       #如果是主键，那就保存起来
                    # 找到主键:
                    if primaryKey:
                        raise StandardError('Duplicate primary key for field: %s' % k)  #主键已存在，报个重复的错
                    primaryKey = k                                      #前面primaryKey = None,现在再赋值
                else:
                    fields.append(k)                                #如果不是主键，在fields结尾添加k的值
                                                                    #   只是属性名，没有值
        if not primaryKey:                                          #没有主键，报个错
            raise StandardError('Primary key not found.')
        for k in mappings.keys():                                   #把所有的映射中的k值都吐出来
            attrs.pop(k)                                            #清空了属性的列表
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))    #`:英文输入法时，Esc下边。数据库中`data`和自带的data区分
                                                                    #map(f = field),将field数据转到了f中。相当于做tmp
                                                                    #   map有两个参数，函数+参数
                                                                    #lambda函数部分f: '`%s`' % f
                                                                    #   f = '`%s`' % f
                                                                    #这一句话的整体意义就是：把field中所有成员
                                                                    #   存放在escaped_fields中
        attrs['__mappings__'] = mappings # 保存属性和列的映射关系      自己定义了一堆属性
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey # 主键属性名
        attrs['__fields__'] = fields # 除主键外的属性名
        #设定好了格式？？？不懂
        #直接调用__select__就可以有这个字符串代入进去了
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
                                                                    #查找     __select__ 添加的属性
                                                                    #这个变量是使用者自己定义的，好好理解
                                                                    #合并成各个成员连接起来的字符转，中间用‘，’隔开
                                                                    #在查询的时候，选定表，各个属性
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
                                                                    #增加
                                                                    #这句话是打印出来看的
                                                                    #在插入的时候，选定表，属性，主键和所有值
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
                                                                    #修改
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
                                                                    #删除
                                                                    #这个删除太狠了，直接找到主键，把一整条数据都删除了
        return type.__new__(cls, name, bases, attrs)                    #固定写法，new需要这么返回，主要是更新了attrs

#通过app.log可以看出来：需要每个model加载一遍（user，blog，comment）
#   加载完这几个表之后，再加载里面的id等，就是把models.py里面的内容同加载进来，日志中就会输出这些内容
#   另外，ORM中的内容只在装载app的时候出现一遍，然后就不用再运行了

class Model(dict, metaclass=ModelMetaclass):                            #定义一个模型层的类！
                                                                        #其实model作为一个字典的子类，另外又
                                                                        #   实现一个方法dict.filed并不是又很多实际作用
                                                                        #   这里面还实现了find的几个函数，另外还有
                                                                        #   增删改查的操作。
    def __init__(self, **kw):                                           #初始化
        super(Model, self).__init__(**kw)                               #   这个初始话厉害了

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

    @classmethod                                                        #类方法
    @asyncio.coroutine
    def findAll(cls, where=None, args=None, **kw):                      #查找
        ' find objects by where clause. '
        sql = [cls.__select__]                                          #在142行处有具体的话
        if where:                                                       #选择查找的条件
            sql.append('where')                                         #   一旦有了要查找的东西，直接架上
                                                                        #   select语句，再外加上查找的内容就行了
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

'''
前面定义的各个操作，比如说select,execute都是留给下面使用的。具体用法上面定义，在这里使用。
所以一个函数可以这样理解，前面书的话都是铺垫，只有在最后是作者的主要想法。 
'''
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
        rows = yield from execute(self.__insert__, args)                #看这个函数，execute里面的参数都传好了
                                                                        #   如果返回状态有问题，下面会给出错误
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
                                                                        #结合着前面的
        args = [self.getValue(self.__primary_key__)]
        rows = yield from execute(self.__delete__, args)
        #attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        #def execute(sql, args, autocommit=True):
        #递归着看回去，找出关系
        #   目前的结论是：execute需要传入两个参数
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)
