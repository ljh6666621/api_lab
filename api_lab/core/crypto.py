import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from core.config import SECRET_KEY


def _derive_fernet_key(master_secret: str) -> bytes:
    """
    根据 SECRET_KEY 通过 SHA256 + base64 派生 Fernet 对称加密密钥。
    保证密钥与 JWT SECRET_KEY 同源，避免引入新的配置项。
    :param master_secret: 原始主密钥（通常是 config.SECRET_KEY）
    :return: 32 字节 base64 编码的 Fernet key（bytes）
    """
    digest = hashlib.sha256(master_secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet_instance: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """
    获取 Fernet 单例（基于 SECRET_KEY 派生）。
    :return: 已初始化的 Fernet 实例
    """
    global _fernet_instance
    if _fernet_instance is None:
        key = _derive_fernet_key(SECRET_KEY)
        _fernet_instance = Fernet(key)
    return _fernet_instance


def encrypt_secret(plain_text: Optional[str]) -> Optional[str]:
    """
    对敏感字段（例如 LLM api_key）进行 Fernet 对称加密。
    明文为 None 或空字符串时原样返回，避免把空值塞进数据库。
    :param plain_text: 明文字符串（如 api_key）
    :return: base64 格式的加密字符串；或 None
    """
    if plain_text is None or plain_text == "":
        return plain_text
    f = _get_fernet()
    token = f.encrypt(plain_text.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(cipher_text: Optional[str]) -> Optional[str]:
    """
    对加密过的敏感字段解密还原。
    入参为 None / 空字符串 或 非法 token 时返回 None（上层需自行处理）。
    :param cipher_text: encrypt_secret 返回的加密字符串
    :return: 明文字符串；或 None（解密失败/缺省）
    """
    if cipher_text is None or cipher_text == "":
        return None
    try:
        f = _get_fernet()
        return f.decrypt(cipher_text.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None
