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

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../')
    from dhcpd import Dhcpd
except ImportError as e:
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)


class TestDhcpdClass(unittest.TestCase):

    def setUp(self):
        with patch("dhcpd.Dhcpd.init_model") as init_model:
            init_model.return_value = True
            self.dhcpd = Dhcpd(connection=Mockup())

    def tearDown(self):
        self.dhcpd.stop()
        self.dhcpd = None

    def test_loadTemplate(self):
        """
        check template is read success or not
        """
        m = mock_open(read_data="mock read $str")
        with patch("dhcpd.open", m, create=True):
            mock_str = Template("mock read ${str}").substitute(str="string")
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
    @patch("dhcpd.Dhcpd.update_config_file")
    def test_init_model(self, update_config_file, sleep):

        # arrange
        update_config_file.return_value = True
        sleep.return_value = True
        with patch("dhcpd.Dhcpd.dhcp_restart") as dhcp_restart:
            dhcp_restart.return_value = True
            with patch("dhcpd.logger.info") as log:
                self.dhcpd.init_model()
                log.assert_called_with("DHCP server initialize success")

        with patch("dhcpd.Dhcpd.dhcp_restart") as dhcp_restart:
            dhcp_restart.return_value = False
            with patch("dhcpd.logger.info") as log:
                self.dhcpd.init_model()
                log.assert_called_with("DHCP server initialize failed")

    @patch("dhcpd.Dhcpd.get_ifcg_interface")
    def test_do_get(self, get_ifcg_interface):
        """
        test do_get should return code 200
        """

        message = Message({"data": {"message": "call get()"},
                          "query": {}, "param": {}})

        def resp1(code=200, data=None):
            self.assertEqual(code, 200)
            self.assertEqual(data, {"currentStatus": ANY, "collection": ANY})
        self.dhcpd.do_get(message=message, response=resp1)

    @patch("dhcpd.Dhcpd.get_ifcg_interface")
    def test_do_get_id(self, get_ifcg_interface):
        """
        test do_get_id with correct id should return code 200
        """

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
        self.dhcpd.do_get_id(message=message, response=resp1)

    @patch("dhcpd.Dhcpd.get_ifcg_interface")
    def test_do_get_invalid_id(self, get_ifcg_interface):
        """
        test do_get_id with invalid id should return code 400
        """
        message = Message({"data": {"message": "call get_id()"},
                          "query": {}, "param": {"id": 5566}})

        def resp2(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invalid Input"})
        self.dhcpd.do_get_id(message=message, response=resp2)

    def test_do_put_id_invalid_input(self):
        """
        test do_put_id with invalid input should return code 400
        """

        message = Message({"data": {"id": 5566, "name": "eth0"},
                          "query": {}, "param": {"id": "test123"}})

        def resp1(code=200, data=None):
            self.assertEqual(code, 400)
        self.dhcpd.do_put_id(message=message, response=resp1)

    @patch("dhcpd.Dhcpd.update_db")
    def test_do_put_id_update_db_failed(self, update_db):
        """
        test do_put_id with update_db failed should return code 400
        """

        message = Message({"data": {"id": 1, "name": "eth0", "enable": 1,
                                    "subnet": "", "netmask": "",
                                    "startIP": "", "endIP": "", "dns": [],
                                    "domainName": "", "leaseTime": "3600"},
                          "query": {}, "param": {"id": 1}})
        update_db.side_effect = Exception("update_db failed")

        def resp2(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Update DB error"})
        self.dhcpd.do_put_id(message=message, response=resp2)

    @patch("dhcpd.Dhcpd.update_config_file")
    @patch("dhcpd.Dhcpd.update_db")
    def test_do_put_id_update_cfg_failed(self, update_db, update_config_file):
        """
        test do_put_id with update_config_file failed should return code 400
        """

        message = Message({"data": {"id": 1, "name": "eth0", "enable": 1,
                                    "subnet": "", "netmask": "",
                                    "startIP": "", "endIP": "", "dns": [],
                                    "domainName": "", "leaseTime": "3600"},
                          "query": {}, "param": {"id": 1}})

        update_config_file.side_effect = Exception("update_config failed")

        def resp3(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Update config error"})
        self.dhcpd.do_put_id(message=message, response=resp3)

    @patch("dhcpd.Dhcpd.get_status")
    @patch("dhcpd.Dhcpd.dhcp_restart")
    @patch("dhcpd.Dhcpd.update_config_file")
    @patch("dhcpd.Dhcpd.update_db")
    def test_do_put_id_dhcp_restart_failed(self, update_db, update_config_file,
                                           dhcp_restart, get_status):
        """
        test do_put_id with dhcp_restart failed should return code 400
        """

        message = Message({"data": {"id": 1, "name": "eth0", "enable": 1,
                                    "subnet": "", "netmask": "",
                                    "startIP": "", "endIP": "", "dns": [],
                                    "domainName": "", "leaseTime": "3600"},
                          "query": {}, "param": {"id": 1}})

        dhcp_restart.return_value = False
        get_status.return_value = True

        def resp4(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Restart DHCP failed"})
        self.dhcpd.do_put_id(message=message, response=resp4)

    @patch("dhcpd.Dhcpd.get_status")
    @patch("dhcpd.Dhcpd.dhcp_restart")
    @patch("dhcpd.Dhcpd.update_config_file")
    @patch("dhcpd.Dhcpd.update_db")
    def test_do_put_id(self, update_db, update_config_file,
                       dhcp_restart, get_status):
        """
        test do_put_id with dhcp_restart Success should return code 200
        """

        message = Message({"data": {"id": 1, "name": "eth0", "enable": 1,
                                    "subnet": "", "netmask": "",
                                    "startIP": "", "endIP": "", "dns": [],
                                    "domainName": "", "leaseTime": "3600"},
                          "query": {}, "param": {"id": 1}})

        dhcp_restart.return_value = True
        get_status.return_value = True

        def resp5(code=200, data=None):
            self.assertEqual(code, 200)
        self.dhcpd.do_put_id(message=message, response=resp5)

    def test_hook_invalid_input(self):
        """
        test hook with message.data didn't has "name" should return code 400
        """

        message = Message({"data": {"message": "call hook()"},
                          "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "Invalid Input"})
        self.dhcpd.hook(message=message, response=resp, test=True)

    @patch("dhcpd.Dhcpd.update_db")
    def test_hook_update_db_failed(self, update_db):
        """
        test hook with update_db failed should return code 400
        """

        message = Message({"data": {"name": "eth0"},
                           "query": {}, "param": {}})
        update_db.side_effect = Exception("update_db failed")

        def resp2(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "DHCP server hook\
                                             ethernet: Update db error"})
        self.dhcpd.hook(message=message, response=resp2, test=True)

    @patch("dhcpd.Dhcpd.get_status")
    @patch("dhcpd.Dhcpd.dhcp_restart")
    @patch("dhcpd.Dhcpd.update_config_file")
    @patch("dhcpd.Dhcpd.update_db")
    def test_hook_update_cfg_failed(self, update_db, update_config_file,
                                    dhcp_restart, get_status):
        """
        test hook with update_config failed should return code 400
        """

        message = Message({"data": {"name": "eth0"},
                           "query": {}, "param": {}})

        update_config_file.side_effect = Exception("update_config failed")

        def resp3(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "DHCP server hook\
                                             ethernet: Update config error"})
        self.dhcpd.hook(message=message, response=resp3, test=True)

    @patch("dhcpd.Dhcpd.get_status")
    @patch("dhcpd.Dhcpd.dhcp_restart")
    @patch("dhcpd.Dhcpd.update_config_file")
    @patch("dhcpd.Dhcpd.update_db")
    def test_hook_dhcp_restart_failed(self, update_db, update_config_file,
                                      dhcp_restart, get_status):
        """
        test hook with dhcp_restart failed should return code 400
        """
        message = Message({"data": {"name": "eth0"},
                           "query": {}, "param": {}})

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
        dhcp_restart.return_value = False

        def resp4(code=200, data=None):
            self.assertEqual(code, 400)
            self.assertEqual(data, {"message": "DHCP server hook\
                                            ethernet: Restart DHCP failed"})
        self.dhcpd.hook(message=message, response=resp4, test=True)

    @patch("dhcpd.Dhcpd.get_status")
    @patch("dhcpd.Dhcpd.dhcp_restart")
    @patch("dhcpd.Dhcpd.update_config_file")
    @patch("dhcpd.Dhcpd.update_db")
    def test_hook(self, update_db, update_config_file,
                  dhcp_restart, get_status):
        """
        test hook should return code 200
        """

        message = Message({"data": {"name": "eth0"},
                           "query": {}, "param": {}})

        update_db.return_value = True
        update_config_file.return_value = True

        def resp5(code=200, data=None):
            self.assertEqual(code, 200)
        self.dhcpd.hook(message=message, response=resp5, test=True)

    @patch("dhcpd.logger")
    def test_update_db(self, logger):
        message = Message({"data": {"id": 1, "name": "eth0"},
                          "query": {}, "param": {"id": 1}})

        self.dhcpd.update_db(message.data)
        logger.debug.assert_called_once_with("update db success")

    def test_get_ifcg_interface(self):

        with patch.object(os, "listdir") as listdir:

            # get interface success
            listdir.return_value = ["eth0"]
            rc = self.dhcpd.get_ifcg_interface()
            self.assertEqual(rc, ["eth0"])

            # get interface failed
            listdir.side_effect = Exception("error excepation!")
            rc = self.dhcpd.get_ifcg_interface()
            self.assertEqual(rc, [])

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

    @patch("dhcpd.logger")
    def test_dhcp_stop(self, logger):

        with patch.object(subprocess, "call") as call:
            call.return_value = 0
            self.dhcpd.dhcp_stop()
            logger.info.assert_called_once_with("DHCP server is stopped")

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

    @patch("dhcpd.logger")
    @patch("dhcpd.Dhcpd.get_ifcg_interface")
    def test_update_config_file(self, get_ifcg_interface, logger):

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

        m = mock_open()
        with patch("dhcpd.open", m, create=True):
            self.dhcpd.update_config_file()
            logger.info.assert_called_once_with("DHCPD config is updated")

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
        self.assertRaises(Exception, self.dhcpd.get_interface_ip)

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
