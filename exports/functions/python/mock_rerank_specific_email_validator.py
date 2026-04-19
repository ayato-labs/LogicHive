import re


def validate_email_format(email):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))
