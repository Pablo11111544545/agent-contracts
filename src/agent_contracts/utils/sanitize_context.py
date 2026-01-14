from __future__ import annotations

import base64
import binascii
import json
import re
from typing import Any, Optional, Tuple


# -----------------------------
# 定数定義
# -----------------------------

# 最大入力長制限（約10MB相当）
MAX_INPUT_LENGTH = 10_000_000

# Magic number signatures（拡張しやすいように定義）
MAGIC_SIGNATURES = [
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),
    (b"PK\x05\x06", "application/zip"),
    (b"PK\x07\x08", "application/zip"),
    (b"\x1f\x8b\x08", "application/gzip"),
    (b"ID3", "audio/mpeg"),
]


# -----------------------------
# Regexes (fast prefilters)
# -----------------------------

_DATA_URI_RE = re.compile(
    r"^data:(?P<mime>[-\w.+]+/[-\w.+]+)?(?P<params>(;[-\w.+]+=[-\w.+]+)*)?(;base64)?,",
    re.IGNORECASE
)

_JWT_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")

_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
_BASE64URL_RE = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")

_BINARY_URL_RE = re.compile(
    r"^https?:\/\/\S+\.(png|jpe?g|gif|webp|bmp|tiff?|avif|pdf|zip|gz|tar|mp3|mp4|mov|m4a|wav|webm)(\?\S*)?$",
    re.IGNORECASE
)


# -----------------------------
# Helpers
# -----------------------------

def _strip_ws(s: str) -> str:
    """空白文字を削除する。"""
    return re.sub(r"\s+", "", s.strip())


def _add_b64_padding(s: str) -> str:
    """Base64パディングを追加する。"""
    return s + "=" * (-len(s) % 4)


def _safe_b64decode_prefix(s: str, *, urlsafe: bool, max_bytes: int = 64) -> Optional[bytes]:
    """
    Magic number判定のため、先頭のみをデコードする。
    
    Args:
        s: デコード対象の文字列
        urlsafe: URLセーフなbase64かどうか
        max_bytes: デコードする最大バイト数
    
    Returns:
        デコードされたバイト列、失敗時はNone
    """
    # 最大入力長チェック（早期リターン）
    if len(s) > MAX_INPUT_LENGTH:
        return None
    
    compact = _strip_ws(s)
    compact = _add_b64_padding(compact)

    # base64 chars needed for max_bytes
    need = ((max_bytes + 2) // 3) * 4
    chunk = compact[:need]

    try:
        if urlsafe:
            # base64url -> base64に変換して厳格検証
            b64 = chunk.replace('-', '+').replace('_', '/')
            b64 = _add_b64_padding(b64)  # padding追加
            return base64.b64decode(b64, validate=True)
        # 標準base64も念のためpadding確保
        chunk = _add_b64_padding(chunk)  # padding追加
        return base64.b64decode(chunk, validate=True)
    except (binascii.Error, ValueError):
        return None


def _classify_magic(prefix: bytes) -> Optional[str]:
    """
    一般的なバイナリ形式のmagic number判定。
    
    MAGIC_SIGNATURES定数を使用して拡張しやすい設計。
    
    Args:
        prefix: 判定対象のバイト列（先頭部分）
    
    Returns:
        検出されたMIMEタイプ、不明な場合はNone
    """
    # 定義済みのmagic signatureをチェック
    for signature, mime_type in MAGIC_SIGNATURES:
        if prefix.startswith(signature):
            return mime_type
    
    # 特殊なケース（複数条件が必要なもの）
    if prefix.startswith(b"RIFF") and b"WEBP" in prefix[:16]:
        return "image/webp"
    if b"ftyp" in prefix[:32]:
        return "video/mp4"
    
    return None


def _looks_like_base64(s: str, *, min_length: int = 128) -> Tuple[bool, Optional[bool]]:
    """
    高精度なbase64/base64url判定。
    
    Args:
        s: 判定対象の文字列
        min_length: base64と判定する最小長
    
    Returns:
        (base64らしいか, URLセーフフラグまたはNone)のタプル
    """
    # 最大入力長チェック（早期リターン）
    if len(s) > MAX_INPUT_LENGTH:
        return False, None
    
    # 空白が含まれていたらbase64ではない（通常のテキスト）
    if re.search(r"\s", s):
        return False, None
    
    compact = _strip_ws(s)
    if len(compact) < min_length:
        return False, None

    if _BASE64_RE.fullmatch(compact):
        urlsafe = False
        padded = _add_b64_padding(compact)
        try:
            base64.b64decode(padded, validate=True)
            return True, False
        except (binascii.Error, ValueError):
            return False, None
    elif _BASE64URL_RE.fullmatch(compact):
        urlsafe = True
        # base64url -> base64に変換して厳格検証
        b64 = compact.replace('-', '+').replace('_', '/')
        padded = _add_b64_padding(b64)
        try:
            base64.b64decode(padded, validate=True)
            return True, True
        except (binascii.Error, ValueError):
            return False, None
    else:
        return False, None


def _is_likely_hex(s: str, *, min_length: int = 128) -> bool:
    """
    16進数エンコードされたバイナリデータかを判定。
    
    Args:
        s: 判定対象の文字列
        min_length: hex dataと判定する最小長
    
    Returns:
        hexエンコードされたデータらしいか
    """
    # 最大入力長チェック（早期リターン）
    if len(s) > MAX_INPUT_LENGTH:
        return False
    
    # 空白が含まれていたらhexデータではない（通常のテキスト）
    if re.search(r"\s", s):
        return False
    
    compact = _strip_ws(s)
    if len(compact) < min_length:
        return False
    if len(compact) % 2 != 0:
        return False
    if not re.fullmatch(r"[0-9a-fA-F]+", compact):
        return False
    try:
        binascii.unhexlify(compact[: min(256, len(compact))])
        return True
    except (binascii.Error, ValueError):
        return False


def _try_parse_jwt_alg(token: str) -> Optional[str]:
    """
    JWTかどうかを強く判定しつつ、header.algを返す。
    
    Args:
        token: 判定対象のトークン文字列
    
    Returns:
        JWTの場合はalgの値、それ以外はNone
    """
    # 最大入力長チェック（早期リターン）
    if len(token) > MAX_INPUT_LENGTH:
        return None
    
    t = token.strip()
    if not _JWT_RE.fullmatch(t):
        return None
    header_b64 = t.split(".", 2)[0]
    try:
        header_json = base64.urlsafe_b64decode(_add_b64_padding(header_b64)).decode("utf-8")
        obj = json.loads(header_json)
        if isinstance(obj, dict) and "alg" in obj:
            return str(obj.get("alg"))
        return None
    except (binascii.Error, ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _safe_truncate(s: str, max_length: int) -> str:
    """
    サロゲートペアを考慮して文字列を安全にtruncateする。
    
    Args:
        s: トランケート対象の文字列
        max_length: 最大文字数
    
    Returns:
        トランケートされた文字列（サロゲートペア対応）
    """
    if len(s) <= max_length:
        return s
    
    truncated = s[:max_length]
    
    # 最後の文字がhigh surrogate（U+D800-U+DBFF）の場合は1文字戻す
    if truncated and 0xD800 <= ord(truncated[-1]) <= 0xDBFF:
        truncated = truncated[:-1]
    
    return truncated


# -----------------------------
# util method (signature compatible)
# -----------------------------

def sanitize_for_llm_util(
    data: Any,
    max_str_length: int = 1000,
    *,
    sanitize_binary_urls: bool = True,
    base64_min_length: int = 128,
    hex_min_length: int = 128,
    classify_base64_magic: bool = True,
) -> Any:
    """
    LLMに渡す前にバイナリデータや長文を安全に処理するユーティリティ関数。
    
    バイナリっぽいデータ（Data URI、JWT、Base64、Hex等）は置換し、
    それ以外の長文は指定された長さでトランケートします。
    
    Args:
        data: サニタイズ対象のデータ（dict, list, str, その他）
        max_str_length: 文字列の最大長（これを超えるとトランケート）
        sanitize_binary_urls: バイナリURLを置換するか（デフォルト: True）
        base64_min_length: Base64と判定する最小文字数（デフォルト: 128）
        hex_min_length: Hexと判定する最小文字数（デフォルト: 128）
        classify_base64_magic: Base64データをmagic numberで分類するか（デフォルト: True）
    
    Returns:
        サニタイズ済みのデータ。元のデータ型の構造を維持します。
    
    Examples:
        >>> # 辞書内の画像Data URIを置換
        >>> sanitize_for_llm_util({"image": "data:image/png;base64,iVBORw..."})
        {'image': '[DATA_URI:image/png]'}
        
        >>> # 長文をトランケート
        >>> sanitize_for_llm_util("This is a long text..." * 100, max_str_length=100)
        'This is a long text...This is a long text...[TRUNCATED:2300]'
        
        >>> # Base64エンコードされた画像を検出
        >>> sanitize_for_llm_util("iVBORw0KGgoAAAANSUhEUgAA..." * 10)
        '[BASE64_DATA:image/png]'
    
    Note:
        - 辞書やリストは再帰的に処理されます
        - 入力が最大長（MAX_INPUT_LENGTH）を超える場合は[OVERSIZED_DATA]を返します
        - サロゲートペアの途中で切断されないよう配慮されています
        - 既存の関数シグネチャとの後方互換性を維持しています
    """

    if isinstance(data, dict):
        return {
            k: sanitize_for_llm_util(
                v,
                max_str_length,
                sanitize_binary_urls=sanitize_binary_urls,
                base64_min_length=base64_min_length,
                hex_min_length=hex_min_length,
                classify_base64_magic=classify_base64_magic,
            )
            for k, v in data.items()
        }

    if isinstance(data, list):
        return [
            sanitize_for_llm_util(
                item,
                max_str_length,
                sanitize_binary_urls=sanitize_binary_urls,
                base64_min_length=base64_min_length,
                hex_min_length=hex_min_length,
                classify_base64_magic=classify_base64_magic,
            )
            for item in data
        ]

    if isinstance(data, str):
        raw = data
        
        # 早期リターン: 最大入力長超過チェック
        if len(raw) > MAX_INPUT_LENGTH:
            return "[OVERSIZED_DATA]"
        
        # 空白文字処理を統一: Data URI判定前に前処理
        s = raw.strip()

        # 1) data URI（長さに依存せず置換、可能ならmime/中身も反映）
        m = _DATA_URI_RE.match(s)
        if m:
            mime = (m.group("mime") or "").lower() if m.group("mime") else None
            detail = mime

            # base64 data URIなら先頭デコードして magic 判定（任意）
            if classify_base64_magic and "base64" in s[: m.end()].lower():
                after_comma = s.split(",", 1)[1] if "," in s else ""
                if after_comma:
                    prefix = _safe_b64decode_prefix(after_comma, urlsafe=False, max_bytes=64)
                    magic = _classify_magic(prefix) if prefix else None
                    if magic:
                        detail = magic

            return f"[DATA_URI:{detail}]" if detail else "[DATA_URI]"

        # 2) JWT（algまで出す）
        alg = _try_parse_jwt_alg(s)
        if alg is not None:
            return f"[JWT:{alg}]"

        # 3) バイナリURL（任意）
        if sanitize_binary_urls and _BINARY_URL_RE.match(s):
            return "[BINARY_URL]"

        # 4) base64 / base64url（画像に限らない、可能ならmagic分類）
        likely_b64, urlsafe = _looks_like_base64(s, min_length=base64_min_length)
        if likely_b64 and urlsafe is not None:
            if classify_base64_magic:
                prefix = _safe_b64decode_prefix(s, urlsafe=urlsafe, max_bytes=64)
                magic = _classify_magic(prefix) if prefix else None
                if magic:
                    return f"[BASE64_DATA:{magic}]"
            return "[BASE64_DATA]"

        # 5) hex-encoded binary
        if _is_likely_hex(s, min_length=hex_min_length):
            return "[HEX_DATA]"

        # 6) その他の長文は常にTRUNCATE（サロゲートペア対応）
        # すべての検出ロジックを通過した後、最後にtruncateチェック
        if len(raw) > max_str_length:
            truncated = _safe_truncate(raw, max_str_length)
            return truncated + f"...[TRUNCATED:{len(raw)}]"

        # どの検出ロジックにも該当しない短い文字列はそのまま返す
        return raw

    return data
