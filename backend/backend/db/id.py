from nanoid import generate


alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890'

def gen_id(length=16):
    return generate(alphabet, length)


def gen_ids(count, length=16):
    return [gen_id(length) for _ in [None]*count]


def get_ids(rows):
    return [row['id'] for row in rows]
