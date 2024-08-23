#!/usr/bin/env bash
die_func() {
        echo "terminated externaly"
        exit 1
}
trap die_func TERM

sleep infinity &
wait
