#!/usr/bin/env python
# encoding: utf-8
from tornado.ioloop import IOLoop
from tornado.web import Application, url
from tornado.options import options, define, parse_command_line
from lib.core import HTTPServer, config_settings, RequestHandler, RestfulApiHandler, ModuleRouter, ProviderManager
import logging
import sys
import os

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

sys.path.append("./modules/")

import tornado.web
#class HtmlHandler(tornado.web.RequestHandler):
class HtmlHandler(RequestHandler):
    '''
    def post(self):
        path = os.path.normpath(self.request.uri).strip('/')
        local_path = os.path.join(self.settings['template_path'], path)
        if not os.path.exists(local_path):
            self.set_status(404)
            return self.write("404 not found")
        return self.render(path, _data=ModuleRouter(self.settings))
    '''


    def post(self):
        uri = os.path.normpath(self.request.uri).strip('/').split('?')[0]
        print uri
        path = self.get_theme() + '/' + uri
        local_path = os.path.join(self.settings['template_path'], path)
        if not os.path.exists(local_path):
            self.set_status(404)
            return self.write("404 not found")

        #解析出provider
        #ps = self.settings['pages'].get(uri)


        #页面使用的provider配置在uri同目录下的.html.data文件中
        #比如页面是/example/example2.html, 则配置文件为：/example/example2.html.data
        data = ProviderManager.getdata(local_path, self)


        return self.render(path, **data)

    def get(self):
        return self.post()

class ApiHandler(RestfulApiHandler):
    def request_dealer(self, method):
        ret = dict()
        return self.write(ret)

		

def make_app(dev=False):
    '''定义url路由和服务选项等'''
    return Application([
        url(r"/api", ApiHandler),
        url(r"/.*", HtmlHandler),
        ],
        debug = dev,
        gzip = True,
        template_path=os.path.join(os.path.dirname(__file__), "templates"),
        static_path=os.path.join(os.path.dirname(__file__), "static"),
        )

def main():
    define("config", type=str, help="path to config file")
    define("dev", type=bool, help="dev mode switch", default=False)
    define("port", type=int, help="port to listen", default=8218)
    define("ac", type=str, help="Access-Control-Allow-Origin", default="*")
    parse_command_line(final=True)
    app = make_app(options.dev)
    server = HTTPServer(app,xheaders=True)
    define("pid", type=int, default=0)
    options.pid = 0
    if not options.dev:
        server.bind(options.port)
        options.pid = server.start(0)  # Forks multiple sub-processes
    else:
        server.listen(options.port)
    app.settings.update(config_settings(options))
    IOLoop.current().start()

if __name__ == '__main__':
    main()
