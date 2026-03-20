from dotenv import load_dotenv

from app.config.schemas import AppSettings

load_dotenv()


def load_settings() -> AppSettings:
    """读取并返回项目统一配置。"""
    return AppSettings.from_env()
