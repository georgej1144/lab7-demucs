import os, platform, shutil, sys, json
import redis
import minio
import requests

# where is redis (localhost if not defined)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# redis log helpers
infoKey = "{}.worker.info".format(platform.node())
debugKey = "{}.worker.debug".format(platform.node())
def log_debug(message, key=debugKey):
    print("DEBUG:", message, file=sys.stdout)
    redisClient = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    redisClient.lpush('logging', f"{debugKey}:{message}")

def log_info(message, key=infoKey):
    print("INFO:", message, file=sys.stdout)
    redisClient = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=0)
    redisClient.lpush('logging', f"{infoKey}:{message}")

# where is rustfs (localhost if not defined)
RUSTFS_HOST = os.getenv("RUSTFS_HOST", "localhost:9000")

# what are rustfs creds
RUSTFS_USER = os.getenv("RUSTFS_USER")
RUSTFS_PASS = os.getenv("RUSTFS_PASS")

mc = minio.Minio(RUSTFS_HOST, access_key=RUSTFS_USER, secret_key=RUSTFS_PASS, secure=False)


track_splits = ["bass", "drums", "other", "vocals"]

# helper to guarantee file name consistency
def filename(hash, exten="mp3", track=None):
        return hash + "." + (track + "." if track else "") + exten

# run forever
while True:
    # catch redis timeouts and KEEP GOING!
    try:
        # pop a message from "toWorker" or wait indef until there is one to pop
        _, raw = r.blpop("toWorker") # first value in tuple is redundent for popping off one list
        # turn the string back into the json format message
        job = json.loads(raw)
        # get and log the hash
        h = job["hash"]

        log_info(f"[worker-loop]: parsing {h}")

        # get object from bucket, put straight to location on disk
        mc.fget_object("queue", filename(h), "/tmp/" + filename(h))

        # users can't actually control this call, all filenames are digests making this not injectable
        rc = os.system(f"python3 -m demucs.separate --mp3 --out /tmp/output /tmp/{filename(h)}")
        if rc != 0:
            # if demucs command failed, log it
            log_info(f"[worker-loop]: demucs failed for {h} [rc={rc}]")
            # just move on to the next message in the queue on failure
            continue

        # for each track type
        for t in track_splits:
            # get file from demucs output dir structure format
            path = f"/tmp/output/htdemucs/{h}/{t}.mp3"
            # put file in our bucket with our name
            mc.fput_object("output", f"{h}.{t}", path)
        log_info(f"[worker-loop]: uploaded tracks for {h}")

        # cleanup our files so we don't bloat the container storage
        shutil.rmtree(f"/tmp/output/htdemucs/{h}")
        os.remove(f"/tmp/{filename(h)}")

        log_info(f"[worker-loop]: cleaned up files for {h}")

        # get the provided callback url to send a callback post request to
        cb = job.get("callback")
        if cb:
            try:
                # send callback request "passing the payload portion of the callback"
                requests.post(cb["url"], json=cb["data"])
            except Exception as e:
                # log that the callback failed for whatever reason, but don't act on it (don't care)
                log_info(f"callback failed: {e}")
    except Exception as e:
        log_info(f"[worker-loop]: Error hit in main loop: {e}")