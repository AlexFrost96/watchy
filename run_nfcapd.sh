#!/bin/bash
IP=$1
PORT=$2
nfcapd -D -p $PORT -w /var/log/netflow/$IP