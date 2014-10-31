#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import unittest
import logging

from sanji.connection.mockup import Mockup
from sanji.message import Message
from mock import patch
# from string import Template
# from mock import Mock
# from mock import mock_open
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
        # case 1: collection=true
        message = Message({"data": {"message": "call get()"},
                          "query": {"collection": "true"}, "param": {}})

        def resp1(code=200, data=None):
            self.assertEqual(code, 200)
            self.assertEqual(data, {"currentStatus": ANY, "collection": ANY})
        self.dhcp.get(message=message, response=resp1, test=True)

        # case 2: collection=false
        message = Message({"data": {"message": "call get()"},
                          "query": {"collection": "false"}, "param": {}})

        def resp2(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invaild Input"})
        self.dhcp.get(message=message, response=resp2, test=True)

    def test_get_id(self):
        # case 1: correct id
        message = Message({"data": {"message": "call get_id()"},
                          "query": {}, "param": {"id": 1}})

        def resp1(code=200, data=None):
            self.assertEqual(code, 200)
            self.assertEqual(data, ANY)
        self.dhcp.get_id(message=message, response=resp1, test=True)

        # case 2: incorrect id
        message = Message({"data": {"message": "call get_id()"},
                          "query": {}, "param": {"id": 5566}})

        def resp2(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invaild ID"})
        self.dhcp.get_id(message=message, response=resp2, test=True)

    @patch("dhcp.Dhcp.dhcp_restart")
    @patch("dhcp.Dhcp.update_config_file")
    @patch("dhcp.Dhcp.update_db")
    def test_put_id(self, update_db, update_config_file, dhcp_restart):
        # case 1: message didn't has "data" attribute
        message = Message({"query": {}, "param": {"id": 1}})

        def resp(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invaild Input"})
        self.dhcp.put_id(message=message, response=resp, test=True)

        # case 2: id is error
        message = Message({"data": {"id": 5566, "name": "eth0"},
                          "query": {}, "param": {"id": "test123"}})

        def resp1(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invaild ID"})
        self.dhcp.put_id(message=message, response=resp1, test=True)

        # case 3: update_db = False
        message = Message({"data": {"id": 1, "name": "eth0"},
                          "query": {}, "param": {"id": 1}})
        update_db.return_value = False

        def resp3(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Update DB error"})
        self.dhcp.put_id(message=message, response=resp3, test=True)

        # case 4: update_config_file = False
        message = Message({"data": {"id": 1, "name": "eth0"},
                          "query": {}, "param": {"id": 1}})
        update_config_file.return_value = False
        update_db.return_value = True

        def resp4(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Update config error."})
        self.dhcp.put_id(message=message, response=resp4, test=True)

        # case 5: dhcp_restart False
        update_db.return_value = True
        update_config_file.return_value = True
        dhcp_restart.return_value = False

        def resp5(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Restart DHCP failed"})
        self.dhcp.put_id(message=message, response=resp5, test=True)

        # case 6: dhcp_restart Success
        update_db.return_value = True
        update_config_file.return_value = True
        dhcp_restart.return_value = True

        def resp6(code=200, data=None):
            self.assertEqual(code, 200)
            self.assertEqual(data, ANY)
        self.dhcp.put_id(message=message, response=resp6, test=True)

        message = Message({"data": {"id": 1, "name": "eth123"},
                          "query": {}, "param": {"id": 1}})
        update_db.return_value = False

        # case 7: name error
        def resp7(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invaild input ID"})
        self.dhcp.put_id(message=message, response=resp7, test=True)

    @patch("dhcp.Dhcp.get_status")
    @patch("dhcp.Dhcp.dhcp_restart")
    @patch("dhcp.Dhcp.update_config_file")
    @patch("dhcp.Dhcp.update_db")
    def test_hook(self, update_db, update_config_file,
                  dhcp_restart, get_status):
        # case 1: message.data didn't has "name" value
        message = Message({"data": {"message": "call hook()"},
                          "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": ANY})
        self.dhcp.hook(message=message, response=resp, test=True)

        # case 2: update_db = False
        message = Message({"data": {"name": "eth0"},
                          "query": {}, "param": {}})

        # with patch("dhcp.Dhcp.update_db") as update_db:
        update_db.return_value = False

        def resp2(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": ANY})
        self.dhcp.hook(message=message, response=resp2, test=True)

        # case 3: update_config_file = False
        message = Message({"data": {"name": "eth0"}, "query": {}, "param": {}})

        update_db.return_value = True
        # with patch("dhcp.Dhcp.update_config_file") as update_config_file:
        update_config_file.return_value = False

        def resp3(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": ANY})
        self.dhcp.hook(message=message, response=resp3, test=True)

        # case 4: dhcp_restart = False
        update_config_file.return_value = True
        # with patch("dhcp.Dhcp.dhcp_restart") as dhcp_restart:
        dhcp_restart.return_value = False

        def resp4(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": ANY})
        self.dhcp.hook(message=message, response=resp4, test=True)

        # case 5: dhcp_restart = True and get_status = True
        dhcp_restart.return_value = True
        # with patch("dhcp.Dhcp.get_status") as get_status:
        get_status.return_value = True

        def resp5(code=200, data=None):
            self.assertEqual(code, 200)
            self.assertEqual(data, ANY)
        self.dhcp.hook(message=message, response=resp5, test=True)


if __name__ == "__main__":
    logger = logging.getLogger("TestDhcpClass")
    unittest.main()
