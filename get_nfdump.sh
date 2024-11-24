#!/bin/bash

#nfdump -R /var/log/netflow -s record/bytes -n 30 -A srcip,dstip  -t 2024/11/22.19:50:00 'net 192.168.50.0/24' -o csv > data.csv
#nfdump -R /var/log/netflow -s record/bytes  -t 2024/11/22.00:00:00 -n 100 -A srcip,dstip  -o csv > data.csv
#nfdump -R /var/log/netflow/10.1.1.1 -s record/bytes -n 100 -A srcip,dstip  'ip 192.168.50.22' -t 2024/11/23.06:00:00  -o csv > data.csv
#nfdump -R /var/log/netflow -s record/bytes -n 10000000 -A srcip,dstip -o csv > data.csv
#nfdump -R /var/log/netflow/ -s record/bytes -n 1000000 'port 80' -A srcip,dstip -o csv > data.csv
#nfdump -R /var/log/netflow -s record/bytes -n 100 -A srcip,dstip -t 2024/11/24.07:00:00 'ip 192.168.50.11' -o csv > data.csv
show_top() {
    local count=${1:-50}
    local time=${2:-false}
    local filter=${3:-false}
    local format=${4:-false}

    if [[ $format == "e" ]]; then
        cmd="nfdump -R /var/log/netflow -s record/bytes -n $count -o extended"
        if [[ $time != false ]];then
            [[ -n $time ]] && cmd+=" -t $time" 
        fi
        if [[ $filter != false ]];then
            [[ -n $filter ]] && cmd+=" '$filter'"
        fi
    else
        cmd="nfdump -R /var/log/netflow -s record/bytes -n $count -A srcip,dstip -o csv"
        if [[ $time != false ]];then
            [[ -n $time ]] && cmd+=" -t $time" 
        fi
        if [[ $filter != false ]];then
            [[ -n $filter ]] && cmd+=" '$filter'"
        fi
        cmd+=" > data.csv"
    fi

    # Print command
    echo "$cmd"
    # Execute command
    eval "$cmd"
}

show_top "$@"