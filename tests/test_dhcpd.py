#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import unittest
import logging
import subprocess

from sanji.connection.mockup import Mockup
from sanji.message import Message
from mock import patch
from string import Template
from mock import Mock
from mock import mock_open
from mock import ANY

logger = logging.getLogger()

# retry times when model initialize
retry_times = 5

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../')
    from dhcpd import Dhcpd
except ImportError as e:
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)


class TestDhcpdClass(unittest.TestCase):

    def setUp(self):
        with patch("dhcpd.Dhcpd.model_init") as model_init:
            model_init.return_value = True
            self.dhcpd = Dhcpd(connection=Mockup())

    def tearDown(self):
        self.dhcpd.stop()
        self.dhcpd = None

    def test_loadTemplate(self):
        # check template is read success or not
        m = mock_open(read_data="mock read $str")
        with patch("dhcpd.open", m, create=True):
            mock_str = Template("mock read ${str}").substitute(str="string")
            # call loadTemplate
            self.dhcpd.loadTemplate()
            # check subnet template
            subnet_template = self.dhcpd.template["subnet"]
            # replace string
            r = dict(str="string")
            subnet_str = subnet_template.substitute(r)
            self.assertEqual(mock_str, subnet_str)
            # check dhcpd.conf template
            dhcp_template = self.dhcpd.template["dhcpd.conf"]
            dhcp_str = dhcp_template.substitute(r)
            self.assertEqual(mock_str, dhcp_str)

    @patch("dhcpd.time.sleep")
    def test_model_init(self, sleep):
        sleep.return_value = True
        # dhcp_restart = True
        # mock dhcp_restart()
        with patch("dhcpd.Dhcpd.dhcp_restart") as dhcp_restart:
            dhcp_restart.return_value = True
            with patch("dhcpd.logger.info") as log:
                self.dhcpd.model_init()
                log.assert_called_once_with("DHCP server initialize success")

        # dhcp_restart = False
        # mock dhcpd_restart()
        with patch("dhcpd.Dhcpd.dhcp_restart") as dhcp_restart:
            dhcp_restart.return_value = False
            with patch("dhcpd.logger.info") as log:
                self.dhcpd.model_init()
                log.assert_called_once_with("DHCP server initialize failed")

    @patch("dhcpd.Dhcpd.get_ifcg_interface")
    def test_get(self, get_ifcg_interface):
        # case 1: default collection=true
        message = Message({"data": {"message": "call get()"},
                          "query": {}, "param": {}})

        def resp1(code=200, data=None):
            self.assertEqual(code, 200)
            self.assertEqual(data, {"currentStatus": ANY, "collection": ANY})
        self.dhcpd.get(message=message, response=resp1, test=True)

    @patch("dhcpd.Dhcpd.get_ifcg_interface")
    def test_get_id(self, get_ifcg_interface):
        # case 1: correct id
        message = Message({"data": {"message": "call get_id()"},
                          "query": {}, "param": {"id": 1}})
        get_ifcg_interface.return_value = ["eth0"]
        self.dhcpd.model.db = {
            "currentStatus": 1,
            "collection": [
                {
                    "id": 1,
                    "enable": 1,
                    "name": "eth0",
                    "subnet": "192.168.0.0",
                    "leaseTime": "5566",
                    "endIP": "192.168.10.50",
                    "startIP": "192.168.10.10",
                    "domainName": "MXcloud115",
                    "domainNameServers":
                    "option domain-name-servers 8.8.8.8;",
                    "netmask": "255.255.0.0",
                    "routers": "192.168.31.115",
                }
            ]
        }

        def resp1(code=200, data=None):
            self.assertEqual(code, 200)
            self.assertEqual(data, ANY)
        self.dhcpd.get_id(message=message, response=resp1, test=True)

        # case 2: incorrect id
        message = Message({"data": {"message": "call get_id()"},
                          "query": {}, "param": {"id": 5566}})

        def resp2(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invaild ID"})
        self.dhcpd.get_id(message=message, response=resp2, test=True)

    @patch("dhcpd.Dhcpd.get_status")
    @patch("dhcpd.Dhcpd.dhcp_restart")
    @patch("dhcpd.Dhcpd.update_config_file")
    @patch("dhcpd.Dhcpd.update_db")
    def test_put_id(self, update_db, update_config_file,
                    dhcp_restart, get_status):
        # case 1: message didn't has "data" attribute
        message = Message({"query": {}, "param": {"id": 1}})

        def resp(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invaild Input"})
        self.dhcpd.put_id(message=message, response=resp, test=True)

        # case 2: id is error
        message = Message({"data": {"id": 5566, "name": "eth0"},
                          "query": {}, "param": {"id": "test123"}})

        def resp1(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invaild ID"})
        self.dhcpd.put_id(message=message, response=resp1, test=True)

        # case 3: update_db = False
        message = Message({"data": {"id": 1, "name": "eth0", "enable": 1},
                          "query": {}, "param": {"id": 1}})
        update_db.return_value = False

        def resp3(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Update DB error"})
        self.dhcpd.put_id(message=message, response=resp3, test=True)

        # case 4: update_config_file = False
        message = Message({"data": {"id": 1, "name": "eth0"},
                          "query": {}, "param": {"id": 1}})
        update_config_file.return_value = False
        update_db.return_value = True

        def resp4(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Update config error."})
        self.dhcpd.put_id(message=message, response=resp4, test=True)

        # case 5: dhcp_restart False
        message = Message({"data": {"id": 1, "name": "eth0", "enable": 1},
                          "query": {}, "param": {"id": 1}})
        update_db.return_value = True
        update_config_file.return_value = True
        dhcp_restart.return_value = False
        get_status.return_value = True

        def resp5(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Restart DHCP failed"})
        self.dhcpd.put_id(message=message, response=resp5, test=True)

        # case 6: dhcp_restart Success
        update_db.return_value = True
        update_config_file.return_value = True
        dhcp_restart.return_value = True
        get_status.return_value = True

        def resp6(code=200, data=None):
            self.assertEqual(code, 200)
            self.assertEqual(data, ANY)
        self.dhcpd.put_id(message=message, response=resp6, test=True)

        message = Message({"data": {"id": 1, "name": "eth123"},
                          "query": {}, "param": {"id": 1}})
        update_db.return_value = False

        # case 7: name error
        def resp7(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invaild input ID"})
        self.dhcpd.put_id(message=message, response=resp7, test=True)

    @patch("dhcpd.Dhcpd.get_status")
    @patch("dhcpd.Dhcpd.dhcp_restart")
    @patch("dhcpd.Dhcpd.update_config_file")
    @patch("dhcpd.Dhcpd.update_db")
    def test_hook(self, update_db, update_config_file,
                  dhcp_restart, get_status):
        # case 1: message.data didn't has "name" value
        message = Message({"data": {"message": "call hook()"},
                          "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": ANY})
        self.dhcpd.hook(message=message, response=resp, test=True)

        # case 2: update_db = False
        message = Message({"data": {"name": "eth0"},
                          "query": {}, "param": {}})

        # with patch("dhcp.Dhcp.update_db") as update_db:
        update_db.return_value = False

        def resp2(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": ANY})
        self.dhcpd.hook(message=message, response=resp2, test=True)

        # case 3: update_config_file = False
        message = Message({"data": {"name": "eth0"}, "query": {}, "param": {}})

        update_db.return_value = True
        # with patch("dhcp.Dhcp.update_config_file") as update_config_file:
        update_config_file.return_value = False

        def resp3(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": ANY})
        self.dhcpd.hook(message=message, response=resp3, test=True)

        # case 4: dhcp_restart = False
        update_config_file.return_value = True
        # with patch("dhcp.Dhcp.dhcp_restart") as dhcp_restart:
        dhcp_restart.return_value = False

        def resp4(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": ANY})
        self.dhcpd.hook(message=message, response=resp4, test=True)

        # case 5: dhcp_restart = True and get_status = True
        dhcp_restart.return_value = True
        # with patch("dhcp.Dhcp.get_status") as get_status:
        get_status.return_value = True

        def resp5(code=200, data=None):
            self.assertEqual(code, 200)
            self.assertEqual(data, ANY)
        self.dhcpd.hook(message=message, response=resp5, test=True)

    def test_update_db(self):
        message = Message({"data": {"id": 1, "name": "eth0"},
                          "query": {}, "param": {"id": 1}})

        rc = self.dhcpd.update_db(message=message)
        self.assertEqual(rc, True)

        # test exception
        with patch.object(self.dhcpd.model, "db") as model_db:
            model_db.__getitem__.side_effect = Exception("error exception!")
            self.dhcpd.update_db(message)

    def test_get_ifcg_interface(self):
        with patch.object(os, "listdir") as listdir:
            # get interface success
            listdir.return_value = ["eth0"]
            rc = self.dhcpd.get_ifcg_interface()
            self.assertEqual(rc, ["eth0"])

            # get interface failed
            listdir.side_effect = Exception("error excepation!")
            self.dhcpd.get_ifcg_interface()

    @patch("dhcpd.Dhcpd.dhcp_start")
    @patch("dhcpd.Dhcpd.dhcp_stop")
    def test_dhcp_restart(self, dhcp_stop, dhcp_start):
        # dhcp start success
        dhcp_start.return_value = True
        rc = self.dhcpd.dhcp_restart()
        self.assertEqual(rc, True)
        # dhcp start failed
        dhcp_start.return_value = False
        rc = self.dhcpd.dhcp_restart()
        self.assertEqual(rc, False)

    def test_dhcp_stop(self):
        with patch.object(subprocess, "call") as call:
            call.return_value = 0
            rc = self.dhcpd.dhcp_stop()
            self.assertEqual(rc, True)

    @patch("dhcpd.Dhcpd.get_ifcg_interface")
    def test_dhcp_start(self, get_ifcg_interface):
        get_ifcg_interface.return_value = ["eth0"]
        with patch.object(subprocess, "call") as call:
            # dhcp start success
            call.return_value = 0
            rc = self.dhcpd.dhcp_start()
            self.assertEqual(rc, True)
            # dhcp start failed
            call.return_value = 1
            rc = self.dhcpd.dhcp_start()
            self.assertEqual(rc, False)

    @patch("dhcpd.Dhcpd.get_ifcg_interface")
    def test_update_config_file(self, get_ifcg_interface):
        # case 1: update config success
        get_ifcg_interface.return_value = ["eth0"]
        # assign db value
        self.dhcpd.model.db = {
            "currentStatus": 1,
            "collection": [
                {
                    "id": 1,
                    "enable": 1,
                    "name": "eth0",
                    "subnet": "192.168.0.0",
                    "leaseTime": "5566",
                    "endIP": "192.168.10.50",
                    "startIP": "192.168.10.10",
                    "dns": ["1.1.1.1", "2.2.2.2", "3.3.3.3"],
                    "domainName": "MXcloud115",
                    "domainNameServers":
                    "option domain-name-servers 8.8.8.8;",
                    "netmask": "255.255.0.0",
                    "routers": "192.168.31.115",
                }
            ]
        }

        # patch open
        m = mock_open()
        with patch("dhcpd.open", m, create=True):
            rc = self.dhcpd.update_config_file()
            self.assertEqual(rc, True)

        # case 2: update config failed
        get_ifcg_interface.return_value = None
        self.dhcpd.model.db = {
            "collection": [
                {
                    "id": 1,
                    "enable": 1,
                    "name": "eth0",
                    "subnet": "192.168.0.0",
                    "leaseTime": "5566",
                    "endIP": "192.168.10.50",
                    "startIP": "192.168.10.10",
                    "dns": [],
                    "domainName": "MXcloud115",
                    "domainNameServers":
                    "option domain-name-servers 8.8.8.8;",
                    "netmask": "255.255.0.0",
                    "routers": "192.168.31.115",
                }
            ]
        }
        # patch open
        m = mock_open()
        with patch("dhcpd.open", m, create=True):
            rc = self.dhcpd.update_config_file()
            self.assertEqual(rc, False)

        # case 3: length of dns is 0
        get_ifcg_interface.return_value = ["eth0"]
        self.dhcpd.model.db = {
            "collection": [
                {
                    "id": 1,
                    "enable": 1,
                    "name": "eth0",
                    "subnet": "192.168.0.0",
                    "leaseTime": "5566",
                    "endIP": "192.168.10.50",
                    "startIP": "192.168.10.10",
                    "dns": [],
                    "domainName": "MXcloud115",
                    "domainNameServers":
                    "option domain-name-servers 8.8.8.8;",
                    "netmask": "255.255.0.0",
                    "routers": "192.168.31.115",
                }
            ]
        }
        m = mock_open()
        with patch("dhcpd.open", m, create=True):
            rc = self.dhcpd.update_config_file()
            self.assertEqual(rc, True)

    @patch("dhcpd.subprocess")
    def test_get_interface_ip(self, subprocess):
        # case 1: subprocess.Popen success
        process_mock = Mock()
        attrs = {"communicate.return_value": ("10.10.10.10/24", "error")}
        process_mock.configure_mock(**attrs)
        subprocess.Popen.return_value = process_mock
        rc = self.dhcpd.get_interface_ip("eth0")
        self.assertEqual(rc, "10.10.10.10")
        # case 2: subprocess.Popen failed
        subprocess.Popen.side_effect = Exception("error exception!")
        self.dhcpd.get_interface_ip("eth0")

    @patch("dhcpd.subprocess")
    def test_get_status(self, subprocess):
        # get status success
        subprocess.call.return_value = 0
        rc = self.dhcpd.get_status()
        self.assertEqual(rc, True)

        # get status failed
        subprocess.call.return_value = 1
        rc = self.dhcpd.get_status()
        self.assertEqual(rc, False)

if __name__ == "__main__":
    logger = logging.getLogger("TestDhcpdClass")
    unittest.main()
