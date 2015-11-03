#!/usr/bin/env python
# -*- coding: utf-8 -*-

class DataProvider(object):
    #数据模块类名必须是DataProvider

    """服务配置"""
    settings = dict()
    def __init__(self, settings):
        """settings为进程配置，进程启动时，选择的config目录ini文件转换后的选项 """
        self.settings = settings
        

    def foo(self, a=None, b=None):
        """示例方法，该方法根据传入参数返回数据"""
        return "result %s %s" % (a,b)
    def foo2(self, arg):
        return "do something with %s" % arg
