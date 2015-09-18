#!/usr/bin/env python
# encoding: utf-8
import tornado.httpserver
import tornado.web
from tornado.util import (import_object, ObjectDict, raise_exc_info,
                                  unicode_type, _websocket_mask)
import json
import calendar, datetime

class HTTPServer(tornado.httpserver.HTTPServer):
    def start(self, num_processes):
        '''
        增加了process_id的返回值。方便识别子进程并初始化logfile等操作。
        '''
        assert not self._started
        self._started = True
        process_id = 0
        if num_processes != 1:
            process_id = process.fork_processes(num_processes)
        sockets = self._pending_sockets
        self._pending_sockets = []
        self.add_sockets(sockets)
        return process_id

def default_json_decoder(obj):
    if isinstance(obj, datetime.datetime):
        if obj.utcoffset() is not None:
            obj = obj - obj.utcoffset()
    millis = int(calendar.timegm(obj.timetuple()) * 1000 + obj.microsecond / 1000 )
    return millis

class RequestHandler(tornado.web.RequestHandler):
    def write(self, chunk):
        """修改了一下json序列化部分。支持datetime数据类型的序列化，datetime结构输出为时间戳（毫秒）
        """
        if self._finished:
            raise RuntimeError("Cannot write() after finish()")
        if not isinstance(chunk, (bytes, unicode_type, dict)):
            message = "write() only accepts bytes, unicode, and dict objects"
            if isinstance(chunk, list):
                message += ". Lists not accepted for security reasons; see http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.write"
            raise TypeError(message)
        if isinstance(chunk, dict):
            chunk = json.dumps(value, default=default_json_decoder).replace("</", "<\\/")
            self.set_header("Content-Type", "application/json; charset=UTF-8")
        chunk = utf8(chunk)
        self._write_buffer.append(chunk)

