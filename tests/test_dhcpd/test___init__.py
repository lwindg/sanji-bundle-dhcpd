#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import sys
import unittest

from mock import patch
from mock import mock_open

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../../")
    from dhcpd import DHCPD
    from dhcpd import Subnet
except ImportError as e:
    print ("Please check the python PATH for import test module. ({})"
           .format(__file__))
    print e
    exit(1)


class TestSubnetClass(unittest.TestCase):

    def setUp(self):
        self.subnet = Subnet({
            "id": 1,
            "name": "eth0",
            "enable": True,
            "netmask": "255.255.255.0",
            "startIp": "192.168.1.100",
            "endIp": "192.168.1.200",
            "domainNameServers": ["8.8.8.8"],
            "domainName": "MOXA",
            "leaseTime": 3600
        })

    @patch("dhcpd.get_ip_by_interface")
    def test_to_convert(self, get_ip_by_interface):
        """Subnet to_convert should return a subset of dhcpd.conf"""
        get_ip_by_interface.return_value = "192.168.1.1"
        config_str = self.subnet.to_config()
        get_ip_by_interface.called_once_with("eth0")
        self.assertEqual("""##################### eth0 ########################
subnet 192.168.1.0 netmask 255.255.255.0 {
    range 192.168.1.100 192.168.1.200;
    default-lease-time 3600;
    max-lease-time 3600;
    option domain-name-servers 8.8.8.8;
    option domain-name "MOXA"
    option routers 192.168.1.1;
}
""", config_str)

    def tearDown(self):
        pass


class TestDHCPDClass(unittest.TestCase):

    def setUp(self):
        path = os.path.abspath(os.path.dirname(__file__) + "/../../")
        self.dhcpd = DHCPD(name="dhcpd", path=path)

    @patch("dhcpd.Service")
    def test_update_service_1(self, Service):
        """Update service should refresh /etc/dhcp/dhcpd.conf and
        restart service if arg restart is True"""
        m = mock_open()
        with patch("dhcpd.open", m, create=True):
            self.dhcpd.update_service(restart=True)
            m.assert_called_with("/etc/dhcp/dhcpd.conf", "w")
            Service.restart.called_once_with(bg=True)

    @patch("dhcpd.Service")
    def test_update_service_2(self, Service):
        """Update service should refresh /etc/dhcp/dhcpd.conf and
        do not restart service if arg restart is False"""
        m = mock_open()
        with patch("dhcpd.open", m, create=True):
            self.dhcpd.update_service(restart=False)
            m.assert_called_with("/etc/dhcp/dhcpd.conf", "w")
            self.assertFalse(Service.restart.called)

    @patch("dhcpd.DHCPD.update_service")
    def test_update(self, update_service):
        """Update a subnet should call update_service and return updated Obj"""
        updated = self.dhcpd.update(id=1, newObj={
            "id": 1,
            "name": "eth0",
            "enable": False,
            "netmask": "255.255.255.0",
            "startIp": "192.168.1.100",
            "endIp": "192.168.1.200",
            "domainNameServers": ["8.8.8.8"],
            "domainName": "MOXA",
            "leaseTime": 3600
        })
        self.assertEqual(updated["enable"], False)
        update_service.called_once_with()

    @patch("dhcpd.DHCPD.update_service")
    def test_update_nonexist(self, update_service):
        """Update a non-exist subnet should return None"""
        self.assertEqual(self.dhcpd.update(id=100, newObj={}), None)

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
