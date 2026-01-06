from nanoid import generate


alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"


def gen_id(length=16):
    return generate(alphabet, length)
