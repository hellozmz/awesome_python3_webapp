#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

import asyncio, os, inspect, logging, functools

from urllib import parse                                        #加载url库，主要是解析的模块

from aiohttp import web                                         #加载web框架

from apis import APIError                                       #加载自己写的apis的出错函数

def get(path):                                                  #留作装饰器来用
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

def get_required_kw_args(fn):                                   #得到请求的参数。作者是要获得传入的参数
    args = []                                                   #保存在列表中
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)                                   #将符合条件的所有名字都存储起来
    return tuple(args)                                          #又把结果放在了元组中，不再可变了

def get_named_kw_args(fn):                                      #得到名字的参数
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:        #和请求相比，条件变宽泛了
            args.append(name)
    return tuple(args)

def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:        #查看参数类型，只有关键字就返回真
                                                                #   *后边的参数
            return True

def has_var_kw_arg(fn):                                         #检测是否有变量
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:         #被python定义的参数，**后边的参数
            return True

def has_request_arg(fn):                                        #检测是否有请求的变量
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

class RequestHandler(object):                                   #处理请求的主函数

    def __init__(self, app, fn):                                #先来一个初始化，将各个变量赋值
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)             #True or False
        self._has_var_kw_arg = has_var_kw_arg(fn)               #调用has_var_kw_arg函数，判断True or False
        self._has_named_kw_args = has_named_kw_args(fn)         #True or False
        self._named_kw_args = get_named_kw_args(fn)             #调用get_named_kw_args函数，得到参数中名字
        self._required_kw_args = get_required_kw_args(fn)

    @asyncio.coroutine
    def __call__(self, request):                                #这个__call__就是把参数取出来。很重要，值得看！！！
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:   #判断至少有一个True才可以
            if request.method == 'POST':                        #处理post请求
                if not request.content_type:                    #处理请求中的类型错误
                    return web.HTTPBadRequest('Missing Content-Type.')  
                ct = request.content_type.lower()
                if ct.startswith('application/json'):
                    params = yield from request.json()
                    if not isinstance(params, dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params = yield from request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':                         #处理get请求
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:                                          #在上一个if判断中已经被赋值，若没有赋值，则重新赋值
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:#即使赋值了，也检查一下有效性
                # remove all unamed kw:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg:
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:
            kw['request'] = request
        # check required kw:
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = yield from self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

def add_static(app):                                            #把/static/文件夹中的文件加到目标文件
                                                                #   添加静态文件路径
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
                                                                #会拼接成路径：./static/
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

def add_route(app, fn):                                         #加入到路径中？？？？？？不理解啊
                                                                #这个是作者提到的注册函数（一个）。下边的是多个的
                                                                #加入的是路径，代表着加入的是加入的模板页面
                                                                #参考day2，我认为是绑定页面的函数
    method = getattr(fn, '__method__', None)                    #主要包括两个方法：get,post
    path = getattr(fn, '__route__', None)                       #传入的路径
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn)) #其实是有默认的方法的，写出来都是查看错误的
                                                                #来看一下啊，一共三个参数，分别代表：
                                                                #   请求的方法，路径，返回的页面！！！！重点！！！

def add_routes(app, module_name):                               #作者提到的注册函数
    n = module_name.rfind('.')                                  #查看一下'.'的个数
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
    for attr in dir(mod):
        if attr.startswith('_'):
            continue
        fn = getattr(mod, attr)
        if callable(fn):
            method = getattr(fn, '__method__', None)
            path = getattr(fn, '__route__', None)
            if method and path:
                add_route(app, fn)                              #调用上边的add_route

#自动把handler模块的所有符合条件的函数注册了，说的有道理啊。
#在还没有请求进来的时候，所有的函数就加载进来了。都已经放到内存中了