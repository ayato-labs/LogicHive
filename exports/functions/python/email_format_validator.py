import re


def validate_email(email):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))
