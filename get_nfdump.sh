#!/bin/bash
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