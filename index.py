#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import os

from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt
from voluptuous import Schema, REMOVE_EXTRA, Required, Optional, In, Any, \
    Length
from dhcpd import DHCPD

from traceback import format_exc


class Index(Sanji):
    _logger = logging.getLogger("sanji.dhcpd.index")

    def init(self, *args, **kwargs):
        path_root = os.path.abspath(os.path.dirname(__file__))
        self.dhcpd = DHCPD(name="dhcpd", path=path_root)

    @Route(methods="get", resource="/network/dhcpd")
    def get(self, message, response):
        status = self.dhcpd.service.status()
        return response(data={
            "status": True if status == 0 else False,
            "collection": self.dhcpd.getAll()
        })

    @Route(methods="get", resource="/network/dhcpd/:id")
    def get_id(self, message, response):
        data = self.dhcpd.get(id=int(message.param["id"]))
        if data is None:
            return response(code=404)

        return response(data=data)

    @Route(methods="put", resource="/network/dhcpd/:id")
    def put_id(self, message, response):
        data = self.dhcpd.update(
            id=int(message.param["id"]), newObj=message.data)
        if data is None:
            return response(code=404)
        return response(data=data)

    IFACE_INFO = Schema(
        {
            Optional("wan"): bool,
            Required("type"):
                In(frozenset(["eth", "wifi-ap", "wifi-client", "cellular"])),
            Required("mode"): In(frozenset(["static", "dhcp"])),
            Optional("name"): Any(str, unicode, Length(1, 255)),
            Optional("actualIface"): Any(str, unicode, Length(1, 255))
        },
        extra=REMOVE_EXTRA)

    @Route(methods="put", resource="/network/interfaces/:ifname")
    def _event_interface_info(self, message):
        info = message.data
        try:
            info = self.IFACE_INFO(info)
        except:
            self._logger.warning(format_exc())
            return

        try:
            name = message.data.get(
                "actualIface",
                message.data.get("interface", message.param["ifname"]))
        except:
            self._logger.error(
                "no interface specified: {}".format(message.data))
            return
        info["name"] = name
        self.dhcpd.update_iface_info(info)


if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=0, format=FORMAT)
    logging.getLogger("sh").setLevel(logging.WARN)
    index = Index(connection=Mqtt())
    index.start()
