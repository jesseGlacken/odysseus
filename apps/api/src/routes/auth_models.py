"""Pydantic v2 request and response models for the auth router.

These models are the source of truth for /api/auth request/response shapes.
They are imported by auth_routes.py for response_model annotations and may be
used by the frontend via packages/contracts.
"""

from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username to authenticate with")
    password: str = Field(..., description="Plain-text password")
    remember: bool = Field(default=True, description="Whether to issue a persistent session cookie")
    totp_code: str | None = Field(default=None, description="Optional TOTP / backup code")


class LoginResponse(BaseModel):
    ok: bool = Field(..., description="Whether login succeeded")
    username: str | None = Field(default=None, description="Authenticated username on success")
    requires_totp: bool | None = Field(
        default=None,
        description="True when password was valid but a TOTP code is required",
    )


class LogoutResponse(BaseModel):
    ok: bool = Field(..., description="Whether logout completed")


class SetupRequest(BaseModel):
    username: str = Field(..., description="Username for the first admin account")
    password: str = Field(..., description="Plain-text password for the first admin")


class SetupResponse(BaseModel):
    ok: bool = Field(..., description="Whether setup succeeded")
    message: str = Field(..., description="Human-readable result message")


class SignupRequest(BaseModel):
    username: str = Field(..., description="Username for the new account")
    password: str = Field(..., description="Plain-text password")


class SignupResponse(BaseModel):
    ok: bool = Field(..., description="Whether account creation succeeded")
    message: str = Field(..., description="Human-readable result message")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., description="Existing password")
    new_password: str = Field(..., description="New password")


class ChangePasswordResponse(BaseModel):
    ok: bool = Field(..., description="Whether the password was changed")


class CreateUserRequest(BaseModel):
    username: str = Field(..., description="Username for the new account")
    password: str = Field(..., description="Plain-text password")
    is_admin: bool = Field(default=False, description="Whether the new account is an admin")


class CreateUserResponse(BaseModel):
    ok: bool = Field(..., description="Whether account creation succeeded")


class DeleteUserRequest(BaseModel):
    username: str = Field(..., description="Username of the account to delete")


class DeleteUserResponse(BaseModel):
    ok: bool = Field(..., description="Whether deletion succeeded")


class RenameUserRequest(BaseModel):
    username: str = Field(..., description="New username")


class RenameUserResponse(BaseModel):
    ok: bool = Field(..., description="Whether the rename succeeded")
    username: str | None = Field(default=None, description="New username")
    renamed_self: bool | None = Field(
        default=None,
        description="True when the admin renamed their own account",
    )


class SetAdminRequest(BaseModel):
    is_admin: bool = Field(..., description="Target admin status")


class SetAdminResponse(BaseModel):
    ok: bool = Field(..., description="Whether the update succeeded")
    is_admin: bool = Field(..., description="Updated admin status")
    self: bool = Field(..., description="True when the acting admin updated themselves")


class SetOpenRegistrationRequest(BaseModel):
    enabled: bool = Field(..., description="Whether open registration is enabled")


class SetOpenRegistrationResponse(BaseModel):
    ok: bool = Field(..., description="Whether the setting was updated")
    signup_enabled: bool = Field(..., description="Current open-registration state")


class AuthStatusResponse(BaseModel):
    configured: bool = Field(..., description="Whether any account exists")
    authenticated: bool = Field(..., description="Whether the caller is logged in")
    username: str | None = Field(default=None, description="Logged-in username")
    is_admin: bool = Field(default=False, description="Whether the logged-in user is an admin")
    privileges: dict[str, Any] | None = Field(
        default=None,
        description="Effective privilege map for the logged-in user",
    )
    signup_enabled: bool | None = Field(
        default=None,
        description="Whether open registration is currently enabled",
    )


class AuthPolicyResponse(BaseModel):
    password_min_length: int = Field(..., description="Minimum allowed password length")
    reserved_usernames: list[str] = Field(..., description="Usernames that cannot be registered")
    signup_enabled: bool = Field(..., description="Whether open registration is currently enabled")
    session_days: int = Field(..., description="Default session lifetime in days")


class TotpSetupResponse(BaseModel):
    secret: str = Field(..., description="Raw TOTP secret (not yet enabled)")
    uri: str = Field(..., description="otpauth:// provisioning URI")
    qr_code: str = Field(..., description="Base64 PNG QR code data URI")


class TotpVerifyRequest(BaseModel):
    code: str = Field(..., description="TOTP code to confirm setup")


class TotpConfirmResponse(BaseModel):
    ok: bool = Field(..., description="Whether 2FA was enabled")
    backup_codes: list[str] = Field(default_factory=list, description="Backup codes")


class TotpDisableRequest(BaseModel):
    password: str = Field(..., description="Account password confirmation")


class TotpDisableResponse(BaseModel):
    ok: bool = Field(..., description="Whether 2FA was disabled")


class TotpStatusResponse(BaseModel):
    enabled: bool = Field(..., description="Whether 2FA is enabled for the caller")


class UserListItem(BaseModel):
    username: str = Field(..., description="Username")
    is_admin: bool = Field(..., description="Admin flag")
    privileges: dict[str, Any] = Field(..., description="Effective privilege map")


class UserListResponse(BaseModel):
    users: list[UserListItem] = Field(..., description="All user accounts")


class UserPrivilegesUpdateResponse(BaseModel):
    ok: bool = Field(..., description="Whether the update succeeded")
    privileges: dict[str, Any] | None = Field(
        default=None,
        description="Updated privilege map",
    )


class FeatureToggleResponse(BaseModel):
    ok: bool = Field(..., description="Whether the toggle succeeded")
    signup_enabled: bool | None = Field(
        default=None,
        description="Current open-registration state after toggle",
    )


class IntegrationListResponse(BaseModel):
    integrations: list[dict[str, Any]] = Field(..., description="Integration definitions")


class IntegrationPresetListResponse(BaseModel):
    presets: dict[str, dict[str, Any]] = Field(..., description="Named integration presets")


class IntegrationItemResponse(BaseModel):
    ok: bool = Field(..., description="Whether the operation succeeded")
    integration: dict[str, Any] = Field(..., description="Integration definition")


class IntegrationTestResponse(BaseModel):
    ok: bool = Field(..., description="Whether the test succeeded")
    message: str = Field(..., description="Human-readable result")
