from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, url
from tornado.httpserver import HTTPServer
import logging
import os
from tornado.options import options, parse_command_line

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class HtmlHandler(RequestHandler):
    def get(self):
        import time
        x = int(self.get_argument('x',0))
        logging.info('request in: %s'%x)
        time.sleep(x)
        print options.as_dict()
        self.write("Hello, world %s" %x)

class ApiHandler(RequestHandler):
    def get(self):
        return self.write('api')
		

def make_app(dev):
    return Application([
        url(r"/api", ApiHandler),
        url(r"/*", HtmlHandler),
        ],
        debug = dev,
        gzip = True,
        template_path=os.path.join(os.path.dirname(__file__), "../../templates"),
        static_path=os.path.join(os.path.dirname(__file__), "../../static"),
        )

def main():
    parse_command_line()
    dev = False
    port = 8218
    app = make_app(dev)
    server = HTTPServer(app,xheaders=True)
    if not dev:
        server.bind(port)
        ret = server.start(0)  # Forks multiple sub-processes
        print 'pid:',ret
    else:
        server.listen(port)
    app.settings['db']=None  # from this point on db is available as self.settings['db']
    IOLoop.current().start()

if __name__ == '__main__':
    main()
