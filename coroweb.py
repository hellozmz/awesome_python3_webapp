#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

import asyncio, os, inspect, logging, functools

from urllib import parse                                        #加载url库，主要是解析的模块

from aiohttp import web                                         #加载web框架

from apis import APIError                                       #加载自己写的apis的出错函数

def get(path):                                                  #留作装饰器来用
                                                                #可以传入参数的
                                                                #   主要功能是得到路径
                                                                #   可以看出来，一共三个def,三个return
    '''
    Define decorator @get('/path')
    '''
    def decorator(func):                                        #定义的这个装饰器，主要就是想要得到路径
                                                                #使用在handlers中
                                                                #   不过，他们是怎么实现的还是不懂
        @functools.wraps(func)                                  #将wrap的属性设置成func的属性
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET'                              #设置get方法
        wrapper.__route__ = path                                #设置route为传入的参数path
        return wrapper
    return decorator

                                                                #装饰器的功能就是传入参数，传入函数，然后进行修饰，处理
def post(path):                                                 #得到path后的路径，怎么得到的就不知道了
                                                                #具体的可以看一下get和post的区别
                                                                #   是否幂等get更加安全，post会修改数据库
    '''
    Define decorator @post('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'                             #只有这一步同GET不同，可是怎么做出来的啊
        wrapper.__route__ = path
        return wrapper
    return decorator

'''
Name    Meaning
POSITIONAL_ONLY         Value must be supplied as a positional argument.
                        Python has no explicit syntax for defining positional-only parameters, but many built-in and 
                            extension module functions (especially those that accept only one or two parameters) accept them.
POSITIONAL_OR_KEYWORD   Value may be supplied as either a keyword or positional argument (this is the standard binding 
                            behaviour for functions implemented in Python.)
VAR_POSITIONAL          A tuple of positional arguments that aren’t bound to any other parameter. This corresponds to 
                            a *args parameter in a Python function definition.
KEYWORD_ONLY            Value must be supplied as a keyword argument. Keyword only parameters are those which appear 
                            after a * or *args entry in a Python function definition.
VAR_KEYWORD             A dict of keyword arguments that aren’t bound to any other parameter. This corresponds to a 
                            **kwargs parameter in a Python function definition.
'''

# ---------------------------- 使用inspect模块中的signature方法来获取函数的参数，实现一些复用功能--
# 关于inspect.Parameter 的  kind 类型有5种：
# POSITIONAL_ONLY       只能是位置参数
# POSITIONAL_OR_KEYWORD 可以是位置参数也可以是关键字参数
# VAR_POSITIONAL        相当于是 *args，位置的参数列表，没有名字的参数列
# KEYWORD_ONLY          关键字参数且提供了key
# VAR_KEYWORD           相当于是 **kw，关键字的参数列表，有名字的参数字典

#   * 用来传递任意个无名字参数，这些参数会一个Tuple的形式访问。
#   参数列存储在元组中
#   ** 用来处理传递任意个有名字的参数，这些参数用dict来访问。
#   参数有名字，保存在字典中

#廖大的意思是想把URL参数和GET、POST方法得到的参数彻底分离。
#
#    GET、POST方法的参数必需是KEYWORD_ONLY
#    URL参数是POSITIONAL_OR_KEYWORD
#    request参数要位于最后一个POSITIONAL_OR_KEYWORD之后的任何地方

'''
def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)           # 是否有request参数
        self._has_var_kw_arg = has_var_kw_arg(fn)             # 是否有变长字典参数
        self._has_named_kw_args = has_named_kw_args(fn)       # 是否存在关键字参数
        self._named_kw_args = get_named_kw_args(fn)           # 所有关键字参数
        self._required_kw_args = get_required_kw_args(fn)     # 所有没有默认值的关键字参数
'''

def get_required_kw_args(fn):                                   #得到请求的参数。作者是要获得传入的参数
                                                                #   针对的主要是没有默认值的参数
    args = []                                                   #保存在列表中
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
                                                                #handler 参数里只有KEYWORD_ONLY 才加入到args列表里。
                                                                #   并且还是没有默认值的
                                                                #   可以看出来，对param的要求很严格，只有关键字才可以
                                                                #如果替换成or param.kind==inspect.Parameter.POSITIONAL_OR_KEYWORD)
                                                                #   greeting(name,request) ==> 可以去掉一个*,
                                                                #   具体问题自己仔细分析
            args.append(name)                                   #将符合条件的所有名字都存储起来
    return tuple(args)                                          #又把结果放在了元组中，不再可变了

def get_named_kw_args(fn):                                      #得到关键字参数 ==> 里面存在关键字
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:        #和请求相比，条件变宽泛了。有默认值的
            args.append(name)
    return tuple(args)

def has_named_kw_args(fn):                                      #存在有关键字的参数 ==> 只是进行检验的
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:        #查看参数类型，只有关键字就返回真
                                                                #   必须是关键字
            return True

def has_var_kw_arg(fn):                                         #检测是否有变长字典参数 ==> 检验
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:         #被python定义的参数，**后边的参数，有名字的参数
                                                                #是关键字的类型，有关键字就行
            return True

def has_request_arg(fn):                                        #检测是否有请求的参数
                                                                #   查看是否存在参数叫做request
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':                                   #有请求出现
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

# RequestHandler目的就是从URL处理函数（如handlers.index）中分析其需要接收的参数，从web.request对象中获取必要的参数，
# 调用URL处理函数，然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求：

class RequestHandler(object):                                   #处理请求的主函数

    def __init__(self, app, fn):                                #先来一个初始化，将各个变量赋值
        self._app = app                                         #前面这两个是需要外来赋值的
        self._func = fn                                         #函数的属性设置为传入的函数
                                                                #接下来的都要用到传入的函数fn
        self._has_request_arg = has_request_arg(fn)             #是否有request参数 ==> True or False
        self._has_var_kw_arg = has_var_kw_arg(fn)               #是否有变长字典参数 ==> True or False
        self._has_named_kw_args = has_named_kw_args(fn)         #是否存在关键字参数 ==> True or False
        self._named_kw_args = get_named_kw_args(fn)             #调用get_named_kw_args函数，所有关键字参数
        self._required_kw_args = get_required_kw_args(fn)       #所有没有默认值的参数

# __call__方法的代码逻辑:
# 1.定义kw对象，用于保存参数
# 2.判断URL处理函数是否存在参数，如果存在则根据是POST还是GET方法将request请求内容保存到kw
# 3.如果kw为空(说明request没有请求内容)，则将match_info列表里面的资源映射表赋值给kw；如果不为空则把命名关键字参数的内容给kw
# 4.完善_has_request_arg和_required_kw_args属性

    @asyncio.coroutine
    def __call__(self, request):                                #这个__call__就是把参数取出来。很重要，值得看！！！
                                                                #RequestHandler目的就是从URL函数中分析其需要接收的参数，
                                                                #   从request中获取必要的参数，调用URL函数，
                                                                #   然后把结果转换为web.Response对象
                                                                #   request就是url请求
        kw = None                                               #这里面的逻辑我还是不清楚，太奇怪了
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:   #判断只要有一个True就可以
                                                                #   也就是说，只要存在参数就可以进行get/post操作
                                                                # required_kw_args是named_kw_args的真子集，第三个条件多余
            if request.method == 'POST':                        #处理post请求
                                                                #   post主要是进行提交数据的，所以下面都是检测格式提交的
                if not request.content_type:                    #查看媒体类型，在http协议消息头中
                    return web.HTTPBadRequest('Missing Content-Type.')  
                ct = request.content_type.lower()               #存在媒体类型，将它转换成小写的类型了，方便接下来的处理
                if ct.startswith('application/json'):           #JSON格式
                    params = yield from request.json()          #获取请求中的json数据
                                                                #   yield from一个线程进行并发处理
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params                                 #得到关键字 ==> 保存json数据，应该是list格式
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                                                                #表单默认的提交数据的格式 或者 表单中进行文件上传
                    params = yield from request.post()
                    kw = dict(**params)                         #得到关键字 ==> 转化成字典的样子
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':                         #处理get请求
                qs = request.query_string                       #取得地址栏参数值
                if qs:
                    kw = dict()                                 #定义一个字典型的关键字字典
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]                            #得到关键字
        if kw is None:                                          #在前几个if判断中已经被赋值，若没有赋值，则重新赋值
                                                                #   没有在GET或POST取得参数，match_info所有到kw中
            kw = dict(**request.match_info)                     #kw是字典形式的，获取的也是字典格式的
        else:                                       #没有变长字典参数且有关键字参数，把关键字提取出来，忽略变长字典参数
            if not self._has_var_kw_arg and self._named_kw_args:#
                                                                #如果没有变长字典参数且有关键字参数，
                                                                #   把所有关键字参数提取出来，忽略所有变长字典参数
                # remove all unamed kw:                         #移除掉所有未被指定的参数
                copy = dict()
                for name in self._named_kw_args:                #在关键字参数中
                    if name in kw:
                        copy[name] = kw[name]                   #这部分似曾相识，把指定的保存起来，未指定的就任他去吧
                kw = copy
            # check named arg:                                  #named被指定的，检测被指定的参数
                                                                #   检查URL参数和http方法得到的参数是否有重合
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:                               #查看请求的参数
                                                                #   完善这个函数
            kw['request'] = request                             #给kw字典加入一项，把request参数提取出来
        # check required kw:
        if self._required_kw_args:                              #检查没有默认值的关键字是否已经赋值
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
                                                                #前边处理，从现在开始调用函数
        logging.info('call with args: %s' % str(kw))            #这句可以在app.log中查看
        try:
            r = yield from self._func(**kw)                     #传入什么函数，就做什么处理
                                                                #   关键是要获取kw参数
                                                                #   主要原因是，kw已经加载完成，所以，
                                                                #   可以把kw当作参数加进去
                                                                #_func是自己加进来的函数，自己想要什么处理，就用什么函数
            return r                                            #返回的是处理好的结果
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

#廖大的意思是想把URL参数和GET、POST方法得到的参数彻底分离。
#
#    GET、POST方法的参数必需是KEYWORD_ONLY
#    URL参数是POSITIONAL_OR_KEYWORD
#    REQUEST参数要位于最后一个POSITIONAL_OR_KEYWORD之后的任何地方

def add_static(app):                                            #把/static/文件夹中的文件加到目标文件
                                                                #   添加静态文件路径
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
                                                                #会拼接成路径：./static/
                                                                #这个路径完全是自己设定
    app.router.add_static('/static/', path)                     #把前面的路径加进来，作为app的static路径
    logging.info('add static %s => %s' % ('/static/', path))

def add_route(app, fn):                                         #注册处理url函数
                                                                #这个是作者提到的注册函数（一个）。下边的是多个的
                                                                #加入的是路径，代表着加入的是加入的模板页面
                                                                #参考day2，我认为是绑定页面的函数
    method = getattr(fn, '__method__', None)                    #主要包括两个方法：get,post
    path = getattr(fn, '__route__', None)                       #传入的路径
                                                                #getattr是python的字自省函数。这句话的意思是：
                                                                #   fn中有__route__属性，输出它的内容，没有输出None(自定义)
                                                                #method, path的内容都定义了
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path,   #get/post, 处理的路径
        fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))   #函数的名字，函数的关键字
    app.router.add_route(method, path, RequestHandler(app, fn)) #其实是有默认的方法的，写出来都是查看错误的
                                                                #来看一下啊，一共三个参数，分别代表：
                                                                #   请求的方法，路径，返回的页面！！！！重点！！！
                                                                #   调用了RequestHandler方法，这个方法是自己定义的
                                                                #   handler=RequestHandler(app,fn)
                                                                #   app.router.add_route(method,path,handler)

def add_routes(app, module_name):                               #作者提到的注册函数，传入的是module_name，
                                                                #   具体使用的时候就是'handlers.py'
    n = module_name.rfind('.')                                  #查看一下'.'最后出现的位置
    if n == (-1):                                               #'.'没有出现
        mod = __import__(module_name, globals(), locals())
    else:                                                       #'.'出现了
        name = module_name[n+1:]                                #显示model_name[n+1],也就是'.'后边所有的内容
                                                                #   其实就是这样的，module_name前边是方法：后边具体名字
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):                                #下划线开始的是requesthandler自己的属性
            continue
        fn = getattr(mod, attr)                                 #找到module的attr属性
        if callable(fn):                                        #fn如果是可以调用的，则进行调用
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)                              #调用上边的add_route

#自动把handler模块的所有符合条件的函数注册了，说的有道理啊。
#在还没有请求进来的时候，所有的函数就加载进来了。都已经放到内存中了
#参考INFO:root:add route POST /api/blogs => api_create_blog(request, name, summary, content)
#   结合handlers.py看