import sys, base64, json, os, io, hashlib, platform
from flask import Flask, request, Response, jsonify
import redis
import minio

app = Flask(__name__)

# where is redis (localhost if not defined)
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# redis log helpers
infoKey = "{}.rest.info".format(platform.node())
debugKey = "{}.rest.debug".format(platform.node())
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

from minio.error import S3Error

# make sure the buckets we use exist, creating any that don't
for name in ["queue", "output"]:
    try:
        if not mc.bucket_exists(name):
            # if the bucket with name doesnt exist, make it
            mc.make_bucket(name)
            log_info(f"[rest]: startup: created bucket {name}")
    except:
        # if we can't make the buckets, bad news. fail.
        raise


@app.route('/', methods=['GET'])
def hello():
    return '<h1> Music Separation Server</h1><p> Use a valid endpoint </p>'

@app.route("/apiv1/separate", methods=["POST"])
def separate():
    log_debug("[rest]: separate: endpoint hit")
    body = request.get_json()
    # get file from req
    data = base64.b64decode(body["mp3"])
    # get file hash
    songhash = hashlib.sha224(data).hexdigest()
    
    # put the file in the rustfs queue bucket 
    mc.put_object("queue", songhash + ".mp3", io.BytesIO(data), len(data))
    
    # create job for file we just put in the bucket (json message telling worker what to do) 
    job = {"hash": songhash, "model": body.get("model"), "callback": body.get("callback")}
    # send the job message to redis message queue
    r.lpush("toWorker", json.dumps(job))
    # log it!
    log_info(f"[rest]: separate: enqueued {songhash}")
    # return json with hash and message
    return jsonify({"hash": songhash, "reason": "Song enqueued for separation"})

@app.route("/apiv1/queue", methods=["GET"])
def queue():
    log_debug("[rest]: queue: endpoint hit")
    # for all messages in "toWorker", get the "hash" field from its JSON and keep it in items
    items = [json.loads(x)["hash"] for x in r.lrange("toWorker", 0, -1)]
    return jsonify({"queue": items})

@app.route("/apiv1/track/<songhash>/<track>", methods=["GET"])
def get_track(songhash, track):
    log_debug("[rest]: get_track: endpoint hit")
    # fetch the track from the output bucket 
    obj = mc.get_object("output", f"{songhash}.{track}")
    # forward the response from the bucket (with non-default mimetype)
        # on failed get from bucket, mimetype won't match lack of content. i dont think i care
    return Response(obj.read(), mimetype="audio/mpeg")

# accept GET and DELETE, get for convenience and DELETE for semantics (rest/README.md)
@app.route("/apiv1/remove/<songhash>/<track>", methods=["GET", "DELETE"])
def remove(songhash, track):
    log_debug("[rest] remove: endpoint hit")
    # remove the track from the output bucket
    mc.remove_object("output", f"{songhash}.{track}")
    # forward the response (good or bad) from the bucket
    return jsonify({"removed": f"{songhash}.{track}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)