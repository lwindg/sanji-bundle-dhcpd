import logging
import sh
import ipaddress

from sh import ErrorReturnCode
from sanji.model import Model
from voluptuous import Schema, REMOVE_EXTRA, Required, Any, Range, All, Length
_logger = logging.getLogger("sanji.dhcpd")

SUBNET_SCHEMA = Schema({
    "id": int,
    Required("name"): All(Any(unicode, str), Length(1, 255)),
    Required("enable"): bool,
    Required("available", default=False): bool,
    Required("netmask"): All(Any(unicode, str), Length(7, 15)),
    Required("startIp"): All(Any(unicode, str), Length(7, 15)),
    Required("endIp"): All(Any(unicode, str), Length(7, 15)),
    Required("domainNameServers"): [Any(unicode, str)],
    Required("domainName"): All(Any(unicode, str), Length(0, 255)),
    Required("leaseTime"): Range(min=60, max=65535)
}, extra=REMOVE_EXTRA)


def get_ip_by_interface(iface):
    ip = sh.awk(
        sh.grep(sh.grep(sh.ip("addr", "show", iface), "inet"),
                "-v", "inet6"), "{print $2}").split("/")[0]
    return ip


class Service(object):
    _logger = logging.getLogger("sanji.dhcpd.service")
    _commands = ["start", "restart", "stop", "status", "daemon_reload", "is_installed"]

    def __init__(self, service_name):
        self.service_name = service_name

    def __getattr__(self, command):
        if command not in self._commands:
            return super(Service, self).__getattr__(command)
        elif command == "is_installed":
            def is_installed(bg=False):
                try:
                    sh.grep(
                        sh.systemctl(
                            "--no-page",
                            "list-unit-files",
                            _bg=bg,
                            _piped=True),
                        self.service_name)
                    return True
                except:
                    return False
            return is_installed
        elif command in ["daemon_reload"]:
            args = []
        elif command in ["start", "restart", "stop", "status"]:
            args=[
                "--no-page",
                command,
                "{}.service".format(self.service_name)]

        def do_command(bg=False):
            try:
                output = sh.systemctl(args,
                    _bg=bg, _no_out=True)
                self._logger.info(
                    "Service '%s' %s" % (self.service_name, command))
                return output.exit_code
            except ErrorReturnCode as e:
                self._logger.info(
                    "Service '%s' %s failed" %
                    (self.service_name, command))
                self._logger.debug(str(e))
                return e.exit_code

        return do_command


class Subnet(dict):
    SUBNET_TMPL = """##################### %(name)s ########################
subnet %(subnetIP)s netmask %(netmask)s {
    range %(startIp)s %(endIp)s;
    default-lease-time %(leaseTime)d;
    max-lease-time %(leaseTime)d;
    option domain-name-servers %(domainNameServers)s;
    %(domainNameString)s
    option routers %(routers)s;
}
"""

    def _convert(self):
        routers = get_ip_by_interface(self["name"])
        ipv4 = ipaddress.IPv4Network(
            (unicode(self["startIp"]), self["netmask"]), strict=False)

        subnetIP = [_ for _ in ipv4.subnets(prefixlen_diff=0)][0]\
            .network_address

        domainNameServers = [_ for _ in self["domainNameServers"]
                             if len(_) > 0]
        subnet = {
            "name": self["name"],
            "subnetIP": subnetIP,
            "netmask": self["netmask"],
            "startIp": self["startIp"],
            "endIp": self["endIp"],
            "leaseTime": self["leaseTime"],
            "routers": routers,
            "domainNameServers": ",".join(domainNameServers),
            "domainNameString": "" if len(self["domainName"]) == 0
            else "option domain-name \"%s\"" % (self["domainName"])
        }

        return subnet

    def to_config(self):
        subnet = self._convert()
        return self.SUBNET_TMPL % (subnet)


class DHCPD(Model):
    DHCPD_SERVICE_PATH = "/etc/systemd/system/isc-dhcp-server-{}.service"
    DHCPD_SERVICE_TMPL = """[Unit]
Description = DHCP server

[Service]
ExecStart = /usr/sbin/dhcpd -q -d --no-pid -cf /etc/dhcp/dhcpd-{}.conf {}

[Install]
WantedBy = multi-user.target
"""
    DHCPD_CONFIG = "/etc/dhcp/dhcpd-{}.conf"
    DHCPD_TMPL = """# MOXA configuration file for ISC dhcpd for Debian
default-lease-time 600;
max-lease-time 7200;

# Use this to send dhcp log messages to a different log file (you also
# have to hack syslog.conf to complete the redirection).
log-facility local7;


#subnet 10.254.239.0 netmask 255.255.255.224 {
#  range 10.254.239.10 10.254.239.20;
#  option routers rtr-239-0-1.example.org, rtr-239-0-2.example.org;
#}
"""
    service = Service("isc-dhcp-server")

    def __init__(self, *args, **kwargs):
        kwargs["schema"] = SUBNET_SCHEMA
        kwargs["model_cls"] = Subnet
        super(DHCPD, self).__init__(*args, **kwargs)

        self.ifaces = []
        self.services = {}

        for subnet in self._getAll():
            self.services[subnet["name"]] = \
                Service("isc-dhcp-server-{}".format(subnet["name"]))
            if self.services[subnet["name"]].is_installed() is False:
                self._install_service(subnet["name"])

        self.update_services()

    def _install_service(self, name):
         with open(self.DHCPD_SERVICE_PATH.format(name), "w") as f:
             dhcpd_service = self.DHCPD_SERVICE_TMPL.format(name, name)
             f.write(dhcpd_service)
             _logger.debug("add dhcpd service for {}".format(name))
             self.services[name].daemon_reload()

    def update_service(self, subnet, restart=True):
        if not self._is_enable(subnet):
            self.services[subnet["name"]].stop()
            return

        # generate config by interface(s)
        with open(self.DHCPD_CONFIG.format(subnet["name"]), "w") as f:
            dhcpd_config = self.DHCPD_TMPL + "\n\n" + subnet.to_config()
            f.write(dhcpd_config)
            _logger.debug("update dhcpd config: %s" % (self.DHCPD_CONFIG))
        self.services[subnet["name"]].restart(bg=True)

    def update_services(self, restart=True):
        """Update dhcpd.config and restart service if restart set to True"""
        for subnet in self._getAll():
            self.update_service(subnet, restart)

    def _is_available(self, iface):
        if iface["wan"] is False and \
                iface["mode"] == "static" and \
                (iface["type"] == "eth" or
                 iface["type"] == "wifi-ap"):
            return True
        else:
            return False

    def _is_enable(self, iface):
        if iface.get("available", False) is True and \
                iface["enable"] is True:
            return True
        else:
            return False

    def get(self, id):
        subnet = super(DHCPD, self).get(id)
        subnet["status"] = True if self.services[subnet["name"]].status() == 0 \
            else False
        return subnet

    def _getAll(self):
        return super(DHCPD, self).getAll()

    def getAll(self):
        subnets = super(DHCPD, self).getAll()
        for subnet in subnets:
            subnet["status"] = True \
                if self.services[subnet["name"]].status() == 0 \
                else False
        return subnets

    def add(self, data):
        raise RuntimeError("Not support Add method")

    def remove(self, id):
        raise RuntimeError("Not support Remove method")

    def update(self, id, newObj):
        """Update an exist subnet, It will restart isc-dhcp-server
           only if update successfully > 0
           Returns:
               newLogProfile(logprofile): udpated logprofile
           Raises:
               ValueError: if device list contains invaild entry
        """
        subnet = self.get(id)
        if subnet is None:
            return None

        # use previous status
        newObj["available"] = subnet["available"]
        newSubnet = super(DHCPD, self).update(id=id, newObj=newObj)
        self.update_service(newSubnet)

        return newSubnet

    def update_iface_info(self, data):
        """Update the interface list.
        available: eth.static, wifi-aplstatic
        unavailable: eth.dhcp, wifi-client.static, wifi-client.dhcp, cellular

            Args:
                data: dict with interface name, type and mode

            type: eth/wifi-ap/wifi-client/cellular
            mode: static/dhcp
            [
                {
                    "name": "eth0",
                    "type": "eth",
                    "mode": "static"
                },
                {
                    "name": "wlan0",
                    "type": "wifi-ap",
                    "mode": "static"
                }
            ]
        """

        # update iface list
        for iface in self.ifaces:
            if iface["name"] == data["name"]:
                iface.update(data)
                break
        else:
            iface = data
            self.ifaces.append(iface)

        # update config
        for subnet in self._getAll():
            if subnet["name"] == iface["name"]:
                enable = self._is_enable(subnet)
                subnet["available"] = self._is_available(iface)
                super(DHCPD, self).update(id=subnet["id"], newObj=subnet)
                self.update_service(subnet)
                _logger.info(
                    "DHCP server for {} is restarted for setting had"
                    "been changed".format(iface["name"]))
                break
