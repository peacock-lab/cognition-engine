"""DeepSeek credential storage backed by macOS Keychain when available."""

from __future__ import annotations

import ctypes
import sys
from dataclasses import dataclass, field
from typing import Literal


DEEPSEEK_KEYCHAIN_SERVICE = "cognition-engine/provider/deepseek"
DEEPSEEK_KEYCHAIN_ACCOUNT = "default"
DEEPSEEK_KEYCHAIN_SECRET_REF = (
    "secret-ref://keychain/cognition-engine/deepseek-api-key"
)

ERR_SEC_SUCCESS = 0
ERR_SEC_DUPLICATE_ITEM = -25299
ERR_SEC_ITEM_NOT_FOUND = -25300


CredentialStoreStatus = Literal[
    "success",
    "unavailable",
    "not_found",
    "failed",
]


@dataclass(frozen=True)
class DeepSeekCredentialLoadResult:
    """Sanitized credential load result.

    The secret value is intentionally hidden from repr so failed tests or
    unexpected exception messages do not print a credential by accident.
    """

    status: CredentialStoreStatus
    backend: str
    blocking_reason: str | None = None
    secret_value: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class DeepSeekCredentialStoreResult:
    """Sanitized credential store result."""

    status: CredentialStoreStatus
    backend: str
    blocking_reason: str | None = None


class DeepSeekCredentialStore:
    """Small protocol-like base class for DeepSeek key storage."""

    backend = "unavailable"

    def load_api_key(self) -> DeepSeekCredentialLoadResult:
        return DeepSeekCredentialLoadResult(
            status="unavailable",
            backend=self.backend,
            blocking_reason="provider_key_store_unavailable",
        )

    def save_api_key(self, secret_value: str) -> DeepSeekCredentialStoreResult:
        _ = secret_value
        return DeepSeekCredentialStoreResult(
            status="unavailable",
            backend=self.backend,
            blocking_reason="provider_key_store_unavailable",
        )


class UnavailableDeepSeekCredentialStore(DeepSeekCredentialStore):
    """Fail-closed store for unsupported platforms or missing frameworks."""

    backend = "unavailable"


class MacOSKeychainDeepSeekCredentialStore(DeepSeekCredentialStore):
    """DeepSeek key storage using macOS Security.framework.

    This adapter does not shell out to the `security` command, so the key is not
    placed in argv, shell history, process listings, or command logs.
    """

    backend = "macos_keychain"

    def __init__(
        self,
        *,
        service: str = DEEPSEEK_KEYCHAIN_SERVICE,
        account: str = DEEPSEEK_KEYCHAIN_ACCOUNT,
    ) -> None:
        self._service = service.encode("utf-8")
        self._account = account.encode("utf-8")
        self._security = ctypes.CDLL(
            "/System/Library/Frameworks/Security.framework/Security"
        )
        self._core_foundation = ctypes.CDLL(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
        self._configure_signatures()

    def load_api_key(self) -> DeepSeekCredentialLoadResult:
        password_length = ctypes.c_uint32()
        password_data = ctypes.c_void_p()
        item_ref = ctypes.c_void_p()
        status = self._security.SecKeychainFindGenericPassword(
            None,
            len(self._service),
            self._service,
            len(self._account),
            self._account,
            ctypes.byref(password_length),
            ctypes.byref(password_data),
            ctypes.byref(item_ref),
        )
        if status == ERR_SEC_ITEM_NOT_FOUND:
            return DeepSeekCredentialLoadResult(
                status="not_found",
                backend=self.backend,
                blocking_reason="provider_key_stored_credential_not_found",
            )
        if status != ERR_SEC_SUCCESS:
            return DeepSeekCredentialLoadResult(
                status="failed",
                backend=self.backend,
                blocking_reason="provider_key_stored_credential_load_failed",
            )
        try:
            secret = ctypes.string_at(
                password_data,
                int(password_length.value),
            ).decode("utf-8")
        finally:
            if password_data:
                self._security.SecKeychainItemFreeContent(None, password_data)
            if item_ref:
                self._core_foundation.CFRelease(item_ref)
        return DeepSeekCredentialLoadResult(
            status="success",
            backend=self.backend,
            secret_value=secret,
        )

    def save_api_key(self, secret_value: str) -> DeepSeekCredentialStoreResult:
        secret_bytes = secret_value.encode("utf-8")
        secret_buffer = ctypes.create_string_buffer(secret_bytes)
        item_ref = ctypes.c_void_p()
        status = self._security.SecKeychainAddGenericPassword(
            None,
            len(self._service),
            self._service,
            len(self._account),
            self._account,
            len(secret_bytes),
            secret_buffer,
            ctypes.byref(item_ref),
        )
        if status == ERR_SEC_SUCCESS:
            if item_ref:
                self._core_foundation.CFRelease(item_ref)
            return DeepSeekCredentialStoreResult(
                status="success",
                backend=self.backend,
            )
        if status == ERR_SEC_DUPLICATE_ITEM:
            return self._update_existing_key(secret_buffer, len(secret_bytes))
        return DeepSeekCredentialStoreResult(
            status="failed",
            backend=self.backend,
            blocking_reason="provider_key_persistent_save_failed",
        )

    def _update_existing_key(
        self,
        secret_buffer: ctypes.Array[ctypes.c_char],
        secret_length: int,
    ) -> DeepSeekCredentialStoreResult:
        password_length = ctypes.c_uint32()
        password_data = ctypes.c_void_p()
        item_ref = ctypes.c_void_p()
        status = self._security.SecKeychainFindGenericPassword(
            None,
            len(self._service),
            self._service,
            len(self._account),
            self._account,
            ctypes.byref(password_length),
            ctypes.byref(password_data),
            ctypes.byref(item_ref),
        )
        try:
            if status != ERR_SEC_SUCCESS:
                return DeepSeekCredentialStoreResult(
                    status="failed",
                    backend=self.backend,
                    blocking_reason="provider_key_persistent_save_failed",
                )
            modify_status = self._security.SecKeychainItemModifyAttributesAndData(
                item_ref,
                None,
                secret_length,
                secret_buffer,
            )
            if modify_status != ERR_SEC_SUCCESS:
                return DeepSeekCredentialStoreResult(
                    status="failed",
                    backend=self.backend,
                    blocking_reason="provider_key_persistent_save_failed",
                )
            return DeepSeekCredentialStoreResult(
                status="success",
                backend=self.backend,
            )
        finally:
            if password_data:
                self._security.SecKeychainItemFreeContent(None, password_data)
            if item_ref:
                self._core_foundation.CFRelease(item_ref)

    def _configure_signatures(self) -> None:
        self._security.SecKeychainAddGenericPassword.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self._security.SecKeychainAddGenericPassword.restype = ctypes.c_int32
        self._security.SecKeychainFindGenericPassword.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        self._security.SecKeychainFindGenericPassword.restype = ctypes.c_int32
        self._security.SecKeychainItemModifyAttributesAndData.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
        ]
        self._security.SecKeychainItemModifyAttributesAndData.restype = ctypes.c_int32
        self._security.SecKeychainItemFreeContent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self._security.SecKeychainItemFreeContent.restype = ctypes.c_int32
        self._core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
        self._core_foundation.CFRelease.restype = None


def build_default_deepseek_credential_store() -> DeepSeekCredentialStore:
    """Build the safest available DeepSeek credential store."""

    if sys.platform != "darwin":
        return UnavailableDeepSeekCredentialStore()
    try:
        return MacOSKeychainDeepSeekCredentialStore()
    except Exception:
        return UnavailableDeepSeekCredentialStore()
