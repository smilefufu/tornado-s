#!/usr/bin/env python
# -*- coding: utf-8 -*-

class DataProvider(object):
    #数据模块类名必须是DataProvider

    """服务配置"""
    settings = dict()
    def __init__(self, settings):
        """settings为进程配置，进程启动时，选择的config目录ini文件转换后的选项 """
        self.settings = settings

    def execute(self, data, handler=None):
        #每个provider只提供唯一的一个execute方法,
        # data: 参数是前面provider的执行结果（provider可以需要前面provider的执行数据），
        # paras: url请求的参数
        # handler: 请求的handler

        d = {}
        d['w'] = handler.get_argument('w', '-')
        d['data'] = [{'title': 'test', 'content':'内容'}, {'title': '标题', 'content':'内容2'}]
        return d
