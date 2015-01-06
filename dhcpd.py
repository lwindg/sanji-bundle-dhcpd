#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
import os
import subprocess
import time
import jsonschema

from sanji.core import Sanji
from sanji.core import Route
from sanji.model_initiator import ModelInitiator
from sanji.connection.mqtt import Mqtt
from string import Template

logger = logging.getLogger()
path_root = os.path.abspath(os.path.dirname(__file__))

PUT_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "enable": {"type": "integer"},
        "subnet": {"type": "string"},
        "netmask": {"type": "string"},
        "startIP": {"type": "string"},
        "endIP": {"type": "string"},
        "dns": {"type": "array"},
        "domainName": {"type": "string"},
        "leaseTime": {"type": "string"}
    },
    "required": ["enable", "id", "name", "subnet", "netmask",
                 "startIP", "endIP", "leaseTime"],
    "additionalProperties": False
}


class Dhcpd(Sanji):

    CONFIG_PATH = "/etc/dhcp/dhcpd.conf"

    def init(self, *args, **kwargs):
        self.model = ModelInitiator("dhcpd", path_root)
        self.permittedName = ["eth0", "eth1", "eth2", "eth3"]
        self.permittedKeys = ["id", "enable", "subnet", "netmask", "startIP",
                              "endIP", "dns", "name",
                              "domainName", "leaseTime"]

        # retry times when model initialize
        self.retry_times = 5

        self.rsp = {}
        self.rsp["code"] = 0
        self.rsp["data"] = None

        # used to save dhcpd.conf
        self.template = dict()
        self.loadTemplate()

    def run(self):
        self.init_model()

    def loadTemplate(self):

        with open(path_root + "/template/subnet", "r") as f:
            self.template["subnet"] = Template(f.read())

        with open(path_root + "/template/dhcpd.conf", "r") as f:
            self.template["dhcpd.conf"] = Template(f.read())

    def init_model(self):
        retry_cnt = 0

        try:
            self.update_config_file()
        except Exception as e:
            logger.debug("Update config error: %s" % e)

        # retry
        while retry_cnt < self.retry_times:

            restart_rc = self.dhcp_restart()

            if restart_rc is True:
                logger.info("DHCP server initialize success")
                return

            retry_cnt = retry_cnt + 1
            time.sleep(10)

        if retry_cnt == self.retry_times:
            logger.info("DHCP server initialize failed")

    @Route(methods="get", resource="/network/dhcpd")
    def get(self, message, response):
        return self.do_get(message, response)

    def do_get(self, message, response):
        # get current exist interface, and return corresponding data
        iface_list = self.get_ifcg_interface()
        rc_data = []
        for item in self.model.db["collection"]:
            if item["name"] in iface_list:
                rc_data.append(item)

        current_status = 1 if self.get_status() else 0

        return response(data={"currentStatus": current_status,
                              "collection": rc_data})

    @Route(methods="get", resource="/network/dhcpd/:id")
    def get_id(self, message, response):
        return self.do_get_id(message, response)

    def do_get_id(self, message, response):
        iface_list = self.get_ifcg_interface()

        for item in self.model.db["collection"]:

            # check interface exist in ifconfig and db
            if (item["id"] == int(message.param["id"])) and \
               item["name"] in iface_list:
                return response(data=item)
        logger.warning("Invalid Input")
        return response(code=400, data={"message": "Invalid Input"})

    @Route(methods="put", resource="/network/dhcpd/:id")
    def put_id(self, message, response):
        return self.do_put_id(message, response)

    def do_put_id(self, message, response):

        try:
            jsonschema.validate(message.data, PUT_SCHEMA)
        except jsonschema.ValidationError:
            logger.warning("Invalid Input")
            response(code=400, data={"message": "Invalid Input"})

        # check put id and db collection id is match
        id_match = False
        for item in self.model.db["collection"]:
            if item["id"] == message.data["id"]:
                id_match = True

        if id_match is False:
            return response(code=400, data={"message": "Invalid ID"})

        put_name = message.data["name"]

        # check name is permitted or not
        if not(put_name in self.permittedName):
            logger.debug("Invalid Name")
            return response(code=400, data={"message": "Invalid Name"})

        try:
            self.update_db(message.data)
            self.model.save_db()
        except Exception as e:
            logger.debug("Update DB error: %s" % e)
            return response(code=400, data={"message": "Update DB error"})

        try:
            self.update_config_file()
        except Exception as e:
            logger.debug("Update config error: %s" % e)
            return response(code=400, data={"message": "Update config error"})

        restart_rc = self.dhcp_restart()

        status_rc = self.get_status()

        # check enable data of id
        enable_flag = False

        if int(message.data["enable"]) == 1:
            enable_flag = True

        if (enable_flag is True) and \
           (restart_rc is False or status_rc is False):
            logger.debug("Restart DHCP failed")
            return response(code=400, data={"message": "Restart DHCP failed"})

        collection_index = message.data["id"] - 1
        return response(data=self.model.db["collection"][collection_index])

    @Route(methods="put", resource="/network/ethernets/:id")
    def hook(self, message, response):

        # check ethernet interface name
        if "name" not in message.data:
            logger.debug("Invalid Input")
            return response(code=400, data={"message": "Invalid Input"})

        hook_name = message.data["name"]
        logger.info("DHCP server is restarting.\
                     Due to %s setting had been chanaged" % hook_name)

        try:
            self.update_db(dict(name=hook_name, enable=0))
            self.model.save_db()
        except Exception as e:
            logger.debug("Hook ethernet update db error: %s" % e)
            return response(code=400, data={"message": "DHCP server hook\
                                             ethernet: Update db error"})

        try:
            self.update_config_file()
        except Exception as e:
            logger.debug("Hook ethernet update config error: %s" % e)
            return response(code=400, data={"message": "DHCP server hook\
                                             ethernet: Update config error"})

        restart_rc = self.dhcp_restart()

        status_rc = self.get_status()

        # check enable data of id
        enable_flag = False

        for item in self.model.db["collection"]:
            if item["name"] == hook_name:
                enable_flag = (item["enable"] == 1)

        if (enable_flag is True) and \
           (restart_rc is False or status_rc is False):
            return response(code=400, data={"message": "DHCP server hook\
                                            ethernet: Restart DHCP failed"})

        return response(data=self.model.db)

    def update_db(self, message):

        # extract data from message by permittedKeys
        data = dict((key, value) for key, value in message.items()
                    if key in self.permittedKeys)

        '''
        find resource id match db data,
        and then update the db data
        '''

        for index, item in enumerate(self.model.db["collection"]):

            # check db id and message,data id is match or not
            if item["id"] == data["id"]:
                db_data = self.model.db["collection"]

                # update db data by dictionary add
                db_data[index] = dict(db_data[index].items() +
                                      data.items())
        logger.debug("update db success")

    def get_ifcg_interface(self):

        # get exist interface
        try:
            interfaces = os.listdir("/sys/class/net")
            rc_interface = [x for x in interfaces if x != "lo"]
            return rc_interface
        except Exception:
            logger.warning("get exist interface failed")
            return []

    def dhcp_restart(self):
        self.dhcp_stop()
        return self.dhcp_start()

    def dhcp_stop(self):
        stop_rc = subprocess.call(["killall", "dhcpd"])

        if stop_rc == 0:
            logger.info("DHCP server is stopped")

    def dhcp_start(self):
        interfaces = self.get_ifcg_interface()
        start_rc = subprocess.call("dhcpd %s" % " ".join(interfaces),
                                   shell=True)
        if start_rc == 0:
            logger.info("DHCP Server start success")
            return True
        else:
            logger.info("DHCP Server start failed")
            return False

    def update_config_file(self):
        subnets = ""
        iface_list = self.get_ifcg_interface()

        for item in [v for v in self.model.db["collection"]]:

            # check if id exist in ifconfig interface or not
            if item["name"] not in iface_list:
                continue

            # check if enable equal to 1 or not
            if item.get("enable", 0) != 1:
                continue

            # get IP from ifconfig and assign to default route
            item["routers"] = self.get_interface_ip(item["name"])

            # if dns_list is empty, we don't put option in settings
            if len(item["dns"]) != 0:
                cmd = ""
                cmd = "option domain-name-servers " + \
                    ", ".join(item["dns"]) + \
                    ";"
                item["domainNameServers"] = cmd
            else:
                item["domainNameServers"] = ""

            # executing template
            subnets += self.template["subnet"].substitute(item) + \
                "\n\n"

        # all subnets template replace in dhcpd.conf
        conf_str = self.template["dhcpd.conf"].substitute(subnets=subnets)

        with open(Dhcpd.CONFIG_PATH, "w") as f:
            f.write(conf_str)

        logger.info("DHCPD config is updated")

    def get_interface_ip(self, iface):
        cmd = ("ip addr show %s | grep inet | grep -v inet6 | awk '{print $2}'"
               % iface)

        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        out = process.communicate()[0]
        ip = out.split("/")[0]
        return ip

    def get_status(self):
        cmd = ("ps aux | grep dhcpd | grep -v grep | grep -v python")
        out = subprocess.call(cmd, shell=True)
        if out == 0:
            return True
        else:
            return False

if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("ssh")

    dhcpd = Dhcpd(connection=Mqtt())
    dhcpd.start()
