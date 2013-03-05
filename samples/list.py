# -*- coding: utf-8 -*-

import redis

r = redis.StrictRedis(unix_socket_path='/tmp/redis.sock')
for i in sorted(r.keys()):
    print(r.get(i))
