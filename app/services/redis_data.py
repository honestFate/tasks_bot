import redis

from redis.commands.json.path import Path

from app.config import settings

r = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    username=settings.redis_username,
    password=settings.redis_password,
    decode_responses=True,
)


def save_to_redis(task_id, data):

    if r.json().set(task_id, Path.root_path(), data):
        r.expire(task_id, 180)
        return True


def get_on_redis(task_id):
    return r.json().get(task_id)


def redis_clear(task_id):
    r.delete(task_id)


if __name__ == '__main__':
    r.delete('00000000002')
