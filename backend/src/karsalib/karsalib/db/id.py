from nanoid import generate


def gen_id(length=16):
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890'
    return generate(alphabet, length)


def get_ids(rows):
    return list(map(
        lambda row: row['id'],
        rows
    ))
