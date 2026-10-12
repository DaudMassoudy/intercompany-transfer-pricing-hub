import os,time,redis
url=os.getenv('REDIS_URL','redis://localhost:6379/0')
while True:
    try:
        r=redis.Redis.from_url(url);r.set('otp-worker-heartbeat',str(time.time()),ex=30)
    except Exception as e:
        print('worker heartbeat error',e,flush=True)
    time.sleep(10)
