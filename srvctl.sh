#!/bin/sh

python server.py -config=config/server.ini 2>/dev/null &

echo $! > srv.pid
