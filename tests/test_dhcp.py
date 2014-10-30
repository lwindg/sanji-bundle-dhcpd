#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import unittest
import logging

from sanji.connection.mockup import Mockup
from sanji.message import Message
from mock import patch
from string import Template
# from mock import Mock
from mock import mock_open
from mock import ANY

logger = logging.getLogger()

# retry times when model initialize
retry_times = 5

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../')
    from dhcp import Dhcp
except ImportError as e:
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)


class TestDhcpClass(unittest.TestCase):

    def setUp(self):
        with patch("dhcp.Dhcp.model_init") as model_init:
            model_init.return_value = True
            self.dhcp = Dhcp(connection=Mockup())

    def tearDown(self):
        self.dhcp.stop()
        self.dhcp = None

    # def test_loadTemplate(self):
    #     # check template is read success or not
    #     m = mock_open(read_data="mock read $str")
    #     with patch("dhcp.open", m, create=True):
    #         mock_str = Template("mock read ${str}").substitute(str="string")
    #         # call loadTemplate
    #         self.dhcp.loadTemplate()
    #         # check subnet template
    #         subnet_template = self.dhcp.template["subnet"]
    #         # replace string
    #         r = dict(str="string")
    #         subnet_str = subnet_template.substitute(r)
    #         self.assertEqual(mock_str, subnet_str)
    #         # check dhcpd.conf template
    #         dhcp_template = self.dhcp.template["dhcpd.conf"]
    #         dhcp_str = dhcp_template.substitute(r)
    #         self.assertEqual(mock_str, dhcp_str)

    # def test_model_init(self):
    #     # dhcp_restart = True
    #     # mock dhcp_restart()
    #     with patch("dhcp.Dhcp.dhcp_restart") as dhcp_restart:
    #         dhcp_restart.return_value = True
    #         with patch("dhcp.logger.info") as log:
    #             self.dhcp.model_init()
    #             log.assert_called_once_with("DHCP server initialize success")

    #     # dhcp_restart = False
    #     # mock dhcp_restart()
    #     with patch("dhcp.Dhcp.dhcp_restart") as dhcp_restart:
    #         dhcp_restart.return_value = False
    #         with patch("dhcp.logger.info") as log:
    #             self.dhcp.model_init()
    #             log.assert_called_once_with("DHCP server initialize failed")

    def test_get(self):
        # case 1: capability
        message = Message({"data": {"message": "call get()"},
                          "query": {}, "param": {}})

        print ("test get message:%s" % message)  
        # def resp(code=200, data=None):
        #     self.assertEqual(code, 200)
        #     self.assertEqual(data, ["eth0"])
        # self.dhcp.get(message=message, response=resp, test=True)

    #     # case 2: collection=true
    #     message = Message({"data": {"message": "call get()"},
    #                       "query": {"collection": "true"}, "param": {}})

    #     def resp1(code=200, data=None):
    #         self.assertEqual(code, 200)
    #         self.assertEqual(data, {"serverEnable": ANY,
    #                                 "serverStatus": ANY, "collection": ANY})
    #     self.dhcp.get(message=message, response=resp1, test=True)

    #     # case 3: collection=false
    #     message = Message({"data": {"message": "call get()"},
    #                       "query": {"collection": "false"}, "param": {}})

    #     def resp2(code=200, data=None):
    #         self.assertEqual(code, 400)
    #         self.assertEqual(data, {"message": "Invaild Input"})
    #     self.dhcp.get(message=message, response=resp2, test=True)

    # def test_get_id(self):
    #     # case 1: correct id
    #     message = Message({"data": {"message": "call get_id()"},
    #                       "query": {}, "param": {"id": "eth0"}})

    #     def resp1(code=200, data=None):
    #         self.assertEqual(code, 200)
    #         self.assertEqual(data, ANY)
    #     self.dhcp.get_id(message=message, response=resp1, test=True)

    #     # case 2: incorrect id
    #     message = Message({"data": {"message": "call get_id()"},
    #                       "query": {}, "param": {"id": "test123"}})

    #     def resp2(code=200, data=None):
    #         self.assertEqual(code, 400)
    #         self.assertEqual(data, {"message": "Invaild ID"})
    #     self.dhcp.get_id(message=message, response=resp2, test=True)

    def test_put_id(self):
        # case 1: message didn't has "data" attribute
        message = Message({"query": {}, "param": {"id": "eth0"}})

        def resp(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invaild Input"})
        self.dhcp.put_id(message=message, response=resp, test=True)

        # case 2: update_db = False
        message = Message({"data": {"id": "eth0"},
                          "query": {}, "param": {"id": "test123"}})
        with patch("dhcp.Dhcp.update_db") as update_db:
            update_db.return_value = False

            def resp1(code=200, data=None):
                self.assertEqual(code, 400)
                self.assertEqual(data, {"message": "Update DB error"})
            self.dhcp.put_id(message=message, response=resp1, test=True)

        # case 3: serverEnable = 0

    # def test_hook(self):
    #     # case 1: message.data didn't has "name" value
    #     message = Message({"data": {"message": "call hook()"},
    #                       "query": {}, "param": {}})

    #     def resp(code=200, data=None):
    #         self.assertEqual(code, 400)
    #         self.assertEqual(data, {"message": ANY})
    #     self.dhcp.hook(message=message, response=resp, test=True)

    #     # case 2: update_db = False
    #     message = Message({"data": {"name": "eth0"},
    #                       "query": {}, "param": {}})

    #     with patch("dhcp.Dhcp.update_db") as update_db:
    #         update_db.return_value = False

    #         def resp1(code=200, data=None):
    #             self.assertEqual(code, 400)
    #             self.assertEqual(data, {"message": ANY})
    #         self.dhcp.hook(message=message, response=resp1, test=True)

    #     # case 3: update_db = True
    #     message = Message({"data": {"name": "eth0"},
    #                       "query": {}, "param": {}})

    #     with patch("dhcp.Dhcp.update_db") as update_db:
    #         update_db.return_value = True
    #         # case 3.1: update_config_file = False
    #         with patch("dhcp.Dhcp.update_config_file") as update_config_file:
    #             update_config_file.return_value = False

    #             def resp2(code=200, data=None):
    #                 self.assertEqual(code, 400)
    #                 self.assertEqual(data, {"message": ANY})
    #             self.dhcp.hook(message=message, response=resp2, test=True)

    #         # case 3.2: update_config_file = True
    #             update_config_file.return_value = True

    #             # case 3.2.1 dhcp_restart = False
    #             with patch("dhcp.Dhcp.dhcp_restart") as dhcp_restart:
    #                 dhcp_restart.return_value = False

    #                 def resp3(code=200, data=None):
    #                     self.assertEqual(code, 400)
    #                     self.assertEqual(data, {"message": ANY})
    #                 self.dhcp.hook(message=message, response=resp3, test=True)

    #             # case 3.2.2 dhcp_restart = True and get_status = True
    #                 dhcp_restart.return_value = True
    #                 with patch("dhcp.Dhcp.get_status") as get_status:
    #                     get_status.return_value = True

    #                     def resp4(code=200, data=None):
    #                         self.assertEqual(code, 200)
    #                         self.assertEqual(data, ANY)
    #                     self.dhcp.hook(message=message, response=resp4,
    #                                    test=True)


if __name__ == "__main__":
    logger = logging.getLogger("TestDhcpClass")
    unittest.main()
