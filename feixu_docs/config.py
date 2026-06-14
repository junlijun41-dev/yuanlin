import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "feixu-dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "feixu.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 上传的模板文件 / 现场影像
    UPLOAD_DIR = os.path.join(BASE_DIR, "instance", "uploads")
    TEMPLATE_DIR = os.path.join(BASE_DIR, "instance", "templates_files")
    EXPORT_DIR = os.path.join(BASE_DIR, "instance", "exports")
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
