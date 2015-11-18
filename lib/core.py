#!/usr/bin/env python
# encoding: utf-8
import tornado.httpserver
import tornado.web
from tornado import process
from tornado.escape import utf8, _unicode
from tornado.util import (unicode_type, ObjectDict)
from tornado.log import LogFormatter
from tornado.options import define
from tornado.util import ObjectDict as ODict
import json, calendar, datetime, ConfigParser, logging, torndb, redis, traceback
import logging
import re
import os
import sys

touch_re = re.compile(r'.*(iOS|iPhone|Android|Windows Phone|webOS|BlackBerry|Symbian|Opera Mobi|UCBrowser|MQQBrowser|Mobile|Touch).*', re.I)

class HTTPServer(tornado.httpserver.HTTPServer):
    def start(self, num_processes):
        '''增加了process_id的返回值。方便识别子进程并初始化不同文件名的logfile等操作。'''
        assert not self._started
        self._started = True
        process_id = 0
        if num_processes != 1:
            process_id = process.fork_processes(num_processes)
        sockets = self._pending_sockets
        self._pending_sockets = []
        self.add_sockets(sockets)
        return process_id

class ModuleRouter(object):
    settings=dict()
    def __init__(self, settings):
        self.settings = settings
    def __getattr__(self, name):
        if len(name.split('_')) == 2: # 调用形式为 modulename_method 格式时，进行的module.method调用
            modulename, method = name.split('_')
            try:
                module = __import__(modulename)
                dp = module.DataProvider(self.settings)
                return getattr(dp, method)
            except:
                import traceback
                logging.info(traceback.format_exc())
                pass
 

class ProviderManager(object):
    #dataprovider管理类，负责解析xx.html.data文件
    Provider_Cache = {}    

    @classmethod
    def loadjson(cls, path):
        file = path
        if not os.path.exists(file):
            file = file.split('/')
            file[1] = 'default'
            file = '/'.join(file)

        if os.path.exists(file):
            fp = open(file, 'r')
            ret = json.loads(fp.read())
            fp.close()
        else:
            ret = {}
        return ret 

    @classmethod
    def getproviders(cls, path, debug):
        path = path + '.data'
        cache = cls.Provider_Cache

        ps = cache.get(path)
        if not ps or debug:
            ps = cls.loadjson(path)

            for p in ps: 
                ret = ps[p]
                m = ret.get('class')
                if not m: m = p
                module = __import__(m)
                ret['module'] = module
                

            cache[path] = ps

        return ps

    @classmethod
    def getdata(cls, path, handler):
        #根据path定义的配置文件执行配置的provider返回执行结果
        debug = handler.settings['debug']
        ps = cls.getproviders(path, debug)

        #依次执行page中配置的provider
        data = {}
        for p in ps:
            ret = ps[p]

            #配置中是否有测试数据, 如果有测试数据，并且是开发模式，则直接使用测试数据
            if not debug or not ret.get('data'):
                dp = ret['module'].DataProvider(handler.settings)
                param = ret.get('param') or {}
                ret = dp.execute(data, handler, **param)
                '''
                try:
                    ret = dp.execute(data, handler, **param)
                except Exception as e:
                    print type(dp)
                    raise e
                '''
            else:
                ret = ret['data']

            if type(ret) == dict:
                ret = ODict(ret)

            data[p] = ret
        data = ODict(data)

        return data      

class RequestHandler(tornado.web.RequestHandler):
    def get_theme(self):
        try:
            ua = self.request.headers.get("User-Agent", "")
            theme = "touch" if touch_re.match(ua) else "default"
        except:
            theme = "default"
        return theme

    def _try_path(self, path):
        pass

    def find_template(self):
        """查找theme所在目录下对应路径的文件进行渲染。
        如果是目录，则查找目录下的index.html并返回渲染相对路径，如果是文件则返回文件相对路径。
        先查找get_theme返回的主题路径，如不存在，再查找default主题下的路径
        返回local_path和tpl_path，前者用于查找数据配置，后者用于渲染参数。
        """
        path = os.path.normpath(self.request.path).strip('/')
        theme = self.get_theme()
        theme_list = ['default'] if theme=='default' else [theme, "default"] 
        tpl_path = None
        for theme in theme_list:
            local_path = os.path.join(self.settings['template_path'], theme, path)
            if not os.path.exists(local_path):
                continue
            if os.path.isdir(local_path):
                local_path = "%s/index.html" % local_path
            if os.path.isfile(local_path):
                tpl_path = local_path.replace(self.settings['template_path'], '')
        return local_path, tpl_path

    def default_json_decoder(self, obj):
        if isinstance(obj, datetime.datetime):
            if obj.utcoffset() is not None:
                obj = obj - obj.utcoffset()
        millis = int(calendar.timegm(obj.timetuple()) * 1000 + obj.microsecond / 1000 )
        return millis
    def write(self, chunk):
        if self._finished:
            raise RuntimeError("Cannot write() after finish()")
        if not isinstance(chunk, (bytes, unicode_type, dict)):
            message = "write() only accepts bytes, unicode, and dict objects"
            if isinstance(chunk, list):
                message += ". Lists not accepted for security reasons; see http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.write"
            raise TypeError(message)
        if isinstance(chunk, dict):
            chunk = json.dumps(chunk, default=self.default_json_decoder).replace("</", "<\\/") #修改了一下json序列化部分。支持datetime数据类型的序列化，datetime结构输出为时间戳（毫秒）
            self.set_header("Content-Type", "application/json; charset=UTF-8")
        chunk = utf8(chunk)
        self._write_buffer.append(chunk)

class RestfulApiHandler(RequestHandler):
    def options(self):
        self.add_header("Access-Control-Allow-Origin", self.settings['ac'])
        return self.write('ok')
    def request_dealer(self, method):
        pass
    def put(self):
        return self.request_dealer('PUT')
    def get(self):
        return self.request_dealer('GET')
    def post(self):
        return self.request_dealer('POST')
    def delete(self):
        return self.request_dealer('DELETE')
    def patch(self):
        return self.request_dealer('PATCH')


        

def config_settings(options):
    '''从options中配置的config文件中读取config数据，以key-value(value是dict形式)加入到options，
    同时默认读取以下项目，并且做对应操作。
    log_file: 配置日志文件名，默认以.log结尾，会在.log前加上_pid来标识不同进程产生的日志文件，主进程（pid=0）不标识pid。
    mysql_*: 配置mysql类型的数据库连接配置，必然有enable,host,port,user,password字段。连接后，将连接对象按以section的名字为key，放到app.setting中。
    redis_*: 类似mysql，字段必然有enable,host,port,password。
    '''
    ret = ObjectDict()
    if not options.config: return ret
    config = ConfigParser.ConfigParser()
    config.read(options.config)
    for section in config.sections():
        if section == 'log_file':
            if options.logging is None or options.logging.lower() == 'none':
                continue
            logger = logging.getLogger()
            logger.setLevel(getattr(logging, options.logging.upper()))
            path = config.get(section, 'path')
            if not path: continue
            path = path.split('.log')[0]
            if options.pid != 0: path += '_%s' % options.pid
            path += '.log'
            # 进行日志文件的配置
            mode = config.get(section, 'mode')
            if mode == 'time':
                try: when = config.get(section, 'interval')
                except: when = 'midnight'
                channel = logging.handlers.TimedRotatingFileHandler(
                        filename=path,
                        when=when,
                        interval=1,
                        backupCount=options.log_file_num_backups)
                pass
            else: # 默认情况下mode是size
                try: block_size = config.getint(section, 'block_size') * 1024 * 1024
                except: block_size = 100000000
                channel = logging.handlers.RotatingFileHandler(
                        filename=path,
                        maxBytes=block_size,
                        backupCount=options.log_file_num_backups)
            channel.setFormatter(LogFormatter(color=False))
            logger.addHandler(channel)
        elif section.find('mysql_')==0: #mysql_开头
            try: enable = config.getint(section, 'enable')
            except: enable = 0
            if enable:
                try:
                    ret[section] = torndb.Connection(
                            host = config.get(section, 'host'),
                            database = config.get(section, 'database'),
                            user = config.get(section, 'user'),
                            password = config.get(section, 'password'),
                            time_zone = "+8:00",
                            )
                except:
                    logging.info(traceback.format_exc())
        elif section.find('redis_')==0:
            try: enable = config.getint(section, 'enable')
            except: enable = 0
            if enable:
                try:
                    ret[section] = redis.Redis(
                            host = config.get(section, 'host'),
                            port = config.getint(section, 'port'),
                            password = config.get(section, 'password'),
                            db = config.getint(section, 'db'),
                            )
                except:
                    logging.info(traceback.format_exc())
                    print traceback.format_exc()
        elif section == 'python_path':
            try: enable = config.getint(section, 'enable')
            except: enable = 0
            if enable:
                try:
                    path_list = config.get(section, 'path').split(':')
                    sys.path += path_list
                except:
                    logging.info(traceback.format_exc())
        else:
            tmp = ObjectDict()
            for key in config.options(section):
                tmp[key] = config.get(section, key)
            ret[section] = tmp
    return ret
        
