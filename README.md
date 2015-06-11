sanji-dhcp [![Build Status](https://travis-ci.org/Sanji-IO/sanji-dhcp.svg?branch=develop)](https://travis-ci.org/Sanji-IO/sanji-dhcp) [![Coverage Status](https://coveralls.io/repos/Sanji-IO/sanji-dhcp/badge.png?branch=develop)](https://coveralls.io/r/Sanji-IO/sanji-dhcp?branch=develop)
==========

sanji-bundle-dhcpd
==================

This bundle provides DHCPD configuration related interfaces.

## Build

```
make dist
make -C build-deb
```

## Commit Changes

Whenever a set of changes are ready to be committed, you should:

1. Update `version` in `bundle.json`.
2. Use `make -C build-deb changelog` to add change-logs.
