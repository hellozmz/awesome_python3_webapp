#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Michael Liao'

'''
async web application.
'''

import logging; logging.basicConfig(level=logging.INFO)             #加入打印日志的模块

import asyncio, os, json, time                                      #加入异步模块，操作系统模块，
from datetime import datetime                                       #加入时间的函数

from aiohttp import web                                             #在异步的框架中，加入web框架
from jinja2 import Environment, FileSystemLoader                    #前端的框架

from config import configs                                          #导入自己的配置

import orm                                                          #导入对象关系映射框架
from coroweb import add_routes, add_static                          #自己重新做的web异步框架

from handlers import cookie2user, COOKIE_NAME

def init_jinja2(app, **kw):                                         #初始化前端模板，传入app框架和关键字参数
    logging.info('init jinja2...')
    options = dict(
        autoescape = kw.get('autoescape', True),                    #jinja2框架中参数
        block_start_string = kw.get('block_start_string', '{%'),    #jinja2框架中参数，运行代码开始标识符
        block_end_string = kw.get('block_end_string', '%}'),        #运行代码的结束标识符
        variable_start_string = kw.get('variable_start_string', '{{'),  #变量开始的标识符
        variable_end_string = kw.get('variable_end_string', '}}'),      #变量结束的标识符，在__base__.html中有这四个变量
        auto_reload = kw.get('auto_reload', True)
    )
    path = kw.get('path', None)                                     #从参数中获取path字段，也就是模板文件的位置
    if path is None:                                                #没有的话，就加入自己的模板，几乎都没有
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates') #前端模板的文件路径=当前路径+templates
                                                                    #   这个templates可以更换名字的，对应的也要把文件夹改名字
    logging.info('set jinja2 template path: %s' % path)             #打印出来：jinja2加载成功
    env = Environment(loader=FileSystemLoader(path), **options)     #jinja2的核心类，功能是保存配置，全局对象和模板路径的
    filters = kw.get('filters', None)                               #传入参数中是否有过滤器这个项，提取出这个参数
    if filters is not None:                                         #有这个参数的值，进行赋值
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env                                     #给模板赋值，前边有了env，存储的模板路径

@asyncio.coroutine                                                  #拦截器中加载的函数
def logger_factory(app, handler):                                   #主要进行在控制窗口打印，注意观察，传入的参数是
                                                                    #   运行的app和处理函数handler。第一个中间层参数
                                                                    #   那么问题来了：
                                                                    #   handler是一个函数，在哪定义的？？？
    @asyncio.coroutine                                              #factory可以理解成组件，集合的意思
    def logger(request):                                            #传入请求
        logging.info('Request: %s %s' % (request.method, request.path))     #输出格式
                                                                    #给出请求的样子
                                                                    #request.method ==> GET, POST
                                                                    #request.path ==> 路径/, /api/manager/, api/blogs
        # yield from asyncio.sleep(0.3)
        return (yield from handler(request))                        #处理好的请求
    return logger                                                   #反正就是按照固定格式往控制窗口中打印输出

@asyncio.coroutine                                                  #拦截器中加载的函数
def auth_factory(app, handler):                                     #验证用户登录
    @asyncio.coroutine                                              #将解析出的cookies用于验证
                                                                    #   后续的URL处理可以拿到登录用户
    def auth(request):
        logging.info('check user: %s %s' % (request.method, request.path))  #在查看用户权限中，查看请求
        request.__user__ = None                                     #先把用户设置成空值
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:                                              #查看用户的类型：并且把当前用户的名字和邮箱
                                                                    #   打印到日志中
                                                                    # 获取到cookie字符串, cookies是用分号分割的一组
                                                                    #   名-值对，在python中被看成dict
            user = yield from cookie2user(cookie_str)               #通过反向解析，获取到用户名（这个得递归着看好多）
            if user:
                logging.info('set current user: %s' % user.email)
                request.__user__ = user
        if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
            return web.HTTPFound('/signin')                         #非管理员想要进行管理，跳转登录页面
        return (yield from handler(request))                        #验证完用户还是要进行处理的，开始handler
    return auth

@asyncio.coroutine                                                  #奇怪了，logging的内容查不到呢
def data_factory(app, handler):                                     #搜集请求的数据
    @asyncio.coroutine
    def parse_data(request):                                        #解析数据，将数据进行部分转化，是它成为可以处理的
        if request.method == 'POST':                                #向服务器提交的数据，两种处理方式
            if request.content_type.startswith('application/json'): #提交数据的类型1
                request.__data__ = yield from request.json()        #主要也就是为了打印日志
                logging.info('request json: %s' % str(request.__data__))                #开始打印日志
            elif request.content_type.startswith('application/x-www-form-urlencoded'):  #提交数据的类型2
                request.__data__ = yield from request.post()
                logging.info('request form: %s' % str(request.__data__))
                                                                    #是这样的，将提交数据的请求区分的更细致了
                                                                    #   处理不同的请求格式
        return (yield from handler(request))                        #将数据处理好了！！这个神奇啊，直接开始处理了
                                                                    #   原因是这样的，这个函数仅仅是中间函数，
                                                                    #   所以，他也就是仅仅把函数过程打印成日志
                                                                    #   不过他没有做什么，要想去具体操作，就要直接
                                                                    #   使用handler 
                                                                    #据说handler(request)是调用了RequestHandler
                                                                    #   这里的request也就是__call__(request)的参数。
    return parse_data

# ***********************************************响应处理（重点，重点，重点，重要的事说三遍）***************************************************
# 总结一下
# 请求对象request的处理工序流水线先后依次是：
#       logger_factory->response_factory->  RequestHandler.__call__->get或post->handler
# 对应的响应对象response的处理工序流水线先后依次是:
#       由handler构造出要返回的具体对象
#       然后在这个返回的对象上加上'__method__'和'__route__'属性，以标识别这个对象并使接下来的程序容易处理
#       RequestHandler目的就是从请求对象request的请求content中获取必要的参数，调用URL处理函数,然后把结果
#       返回给response_factory
#       response_factory在拿到经过处理后的对象，经过一系列类型判断，构造出正确web.Response对象，以正确的方式
#       返回给客户端
# 在这个过程中，我们只用关心我们的handler的处理就好了，其他的都走统一的通道，如果需要差异化处理，就在通道中
#       选择适合的地方添加处理代码。
# 注： 在response_factory中应用了jinja2来渲染模板文件

@asyncio.coroutine
def response_factory(app, handler):                                 #处理后中间层：视图层：就是处理层.传入的handler
                                                                    #   根据控制层传过来的不同数据，产生不同的响应
    @asyncio.coroutine
    def response(request):
        logging.info('Response handler...')                         #先打印个状态，这个输出了好多次
                                                                    #   这个是已经开始回复了
        r = yield from handler(request)                             #从请求中处理得到结果
        if isinstance(r, web.StreamResponse):                       #不同条件进行不同的处理
                                                                    #   主要是根据r的类别进行分类的
            return r                                                #判断是否为web回复流
        if isinstance(r, bytes):                                    #返回True or False
            resp = web.Response(body=r)                             #判断是否为二进制。若是，记录上
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):                                      #判断是否为字符串
            if r.startswith('redirect:'):                           #再判断是否为以redirect开始
                return web.HTTPFound(r[9:])                         #是的话，跳过重定向这个字段
            resp = web.Response(body=r.encode('utf-8'))             #转化成utf8形式
            resp.content_type = 'text/html;charset=utf-8'           #并且标记好格式
            return resp
        if isinstance(r, dict):                                     #判断是否为字典
            template = r.get('__template__')                        #get是由哪里来的很奇怪？？？
            if template is None:                                    #template存在与不存在，进行不同处理
                                                                    #没有模板的情况下，输出模式变为json格式
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:                                                   #有模板的情况下，利用模板进行渲染
                r['__user__'] = request.__user__
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                                                                    #render设置渲染方式？
                                                                    #构造Response对象
                resp.content_type = 'text/html;charset=utf-8'       #   返回去的类型是html
                return resp
        if isinstance(r, int) and t >= 100 and t < 600:
            return web.Response(t)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        # default:
        resp = web.Response(body=str(r).encode('utf-8'))            #再对返回的值进行一个处理，然后
        resp.content_type = 'text/plain;charset=utf-8'              #再处理一下子类型，就可以返回了
                                                                    #   返回的格式是无格式，这也就是编辑不出来
                                                                    #   效果的原因了吧
        return resp
    return response                                                 #可以看出来，只是做了点打印日志，分类的事，具体
                                                                    #   处理不是在这里处理的

def datetime_filter(t):                                             #时间过滤器函数。传入的是写入时间
                                                                    #   传出的是时间间隔
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)                           #一天86400秒，用的可是地板除啊
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

@asyncio.coroutine                                                  #整个函数的入口
def init(loop):
    yield from orm.create_pool(loop=loop, **configs.db)             #加入orm中的pool，这个池的实现参见其具体实现
                                                                    #   在config_default.py中，
                                                                    #   属性为登录数据库的参数：用户密码数据库等
    app = web.Application(loop=loop, middlewares=[                  #app中加入好多参数，参考图片，loop为传入参数，
        logger_factory, auth_factory, response_factory              #   处理前的中间件。整体参见图片
                                                                    #   这三个参数都在前面定义了，都属于中间层的函数
                                                                    #   middlewares是一种拦截器，一个URL在被某个函数处理前，
                                                                    #   可以经过一系列的middleware的处理。
    ])
    init_jinja2(app, filters=dict(datetime=datetime_filter))        #在前端框架jinja2中加入时间过滤器
                                                                    #接下来是作者的自注册支持，开始注册函数
    add_routes(app, 'handlers')                                     #类比来看：选择路径，完全依靠handlers这个文件
                                                                    #   handlers就是所有处理逻辑的函数库啊，一旦
                                                                    #   博客整体框架单间完成，就可以在handlers中
                                                                    #   加入各个路径的处理函数。一个小宝藏！
                                                                    #   自己可以在这里面加入自己想要的各个功能
                                                                    #这不是什么handlers库，而是handlers.py
                                                                    #   处理函数都在handlers.py中
                                                                    #   注册顺序是按照处理函数名字的正序排列
                                                                    #   都是被@get和@post装饰的函数
    add_static(app)                                                 #加载静态文件，查了一下coroweb，有说明
                                                                    #   把/static/文件夹下的内容加进来
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)      #创建了一个服务器
                                                                    #选择本地的路径和端口号
    logging.info('server started at http://127.0.0.1:9000...')      #打印给人看的话
    return srv

loop = asyncio.get_event_loop()                                     #和app_1.py相似，使用框架中的循环
loop.run_until_complete(init(loop))                                 #天荒地老的循环。注意里边的init，在上边的函数，
#loop.run_until_complete( asyncio.wait([init( loop )]) )            #   返回的是服务器端的服务（nginx）
loop.run_forever()

#在浏览器中，request和response是一对的。
#请求来自url，也就是request，经过自己的一堆处理，给出一个response
#处理url的函数可以传入参数request，不过request参数都是可以被省略掉的

#web.Response是给出的应答，返回给客户看的
#   你给他一条请求，他回复你一个应答
#app.router.add_route处理url的函数，接收请求，匹配出对应的返回函数。
#   可以看出来，这个需要引用上面的函数，把上边构造出来的应答页面展示给用户