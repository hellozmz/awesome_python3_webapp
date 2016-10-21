import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

def index(request):
    return web.Response(body=b'<h1>Awesome</h1>')       #返回一句话

@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)                    #这框架也太好用了吧，一个web.app全部调用出来了
    app.router.add_route('GET', '/', index)             #选择路径，get到路径就可以把index返回去
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)  #选择IP和端口
    logging.info('server started at http://127.0.0.1:9000...')                  #打印处信息给调试人员看的
    return srv                                          #返回的是srv line16写的

'''
函数主题
主要就是一个loop函数
'''
loop = asyncio.get_event_loop()                         #传入的话：无限循环
loop.run_until_complete(init(loop))                     #这并行的也真是牛逼，就是不停下来
loop.run_forever()                                      #run forever!!!