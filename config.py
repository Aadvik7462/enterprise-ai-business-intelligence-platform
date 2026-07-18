import os


class Config:
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "ai_bi_secret_key"
    )

    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

    MAX_CONTENT_LENGTH = 100 * 1024 * 1024

    SESSION_PERMANENT = False

    JSON_SORT_KEYS = False

    TEMPLATES_AUTO_RELOAD = True

    SEND_FILE_MAX_AGE_DEFAULT = 0

    ALLOWED_EXTENSIONS = {
        "csv",
        "xlsx",
        "xls"
    }