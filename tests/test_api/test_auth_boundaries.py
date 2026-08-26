"""Guards for the authentication boundary.

Before this branch the API had 56 routes and no authentication dependency:
jwt.encode ran at login, the only jwt.decode merely chose which projects to
return, and it fell through to trusting an unauthenticated X-User-Id header.
The frontend meanwhile signed in anyone who typed anything into the form.

These tests pin the parts that must not quietly relax again.
"""
import pytest

from src.config import SecurityConfigurationError, Settings, validate_security_settings


class TestAdminRoutesRequireCredentials:
    """/auth/admin/* listed every user and deleted arbitrary ones, unauthenticated."""

    @pytest.mark.asyncio
    async def test_admin_stats_rejects_anonymous_callers(self, client):
        response = await client.get("/api/v1/auth/admin/stats")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_delete_rejects_anonymous_callers(self, client):
        response = await client.delete(
            "/api/v1/auth/admin/users/00000000-0000-0000-0000-000000000002"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_a_malformed_token_is_rejected_not_ignored(self, client):
        # The old code caught the decode failure and carried on as anonymous.
        response = await client.get(
            "/api/v1/auth/admin/stats",
            headers={"Authorization": "Bearer not-a-real-token"},
        )
        assert response.status_code == 401


class TestProjectsRequireAuthentication:
    @pytest.mark.asyncio
    async def test_listing_projects_requires_a_token(self, client):
        response = await client.get("/api/v1/projects")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_x_user_id_header_is_not_an_identity(self, client):
        # Setting one header used to be enough to read another user's projects.
        response = await client.get(
            "/api/v1/projects",
            headers={"X-User-Id": "00000000-0000-0000-0000-000000000001"},
        )
        assert response.status_code == 401


class TestGoogleSignInCannotBeFaked:
    @pytest.mark.asyncio
    async def test_empty_payload_is_rejected(self, client):
        # This used to return a fabricated scholar.researcher@gmail.com profile
        # that the frontend accepted as a successful sign-in.
        response = await client.post("/api/v1/auth/google", json={})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_a_self_declared_email_is_not_an_identity(self, client):
        response = await client.post(
            "/api/v1/auth/google",
            json={"email": "someone.else@example.com", "name": "Someone Else"},
        )
        assert response.status_code == 401


class TestHealthDoesNotLeakConfiguration:
    @pytest.mark.asyncio
    async def test_no_api_key_prefixes(self, client):
        # /health is public. It used to publish the first ten characters of the
        # OpenAI and Gemini keys, which is how a live deployment was found to be
        # running with a placeholder key.
        response = await client.get("/health")
        body = response.json()
        assert "openai_key_prefix" not in body
        assert "gemini_key_prefix" not in body


class TestStartupRefusesUnsafeConfiguration:
    def test_missing_secret_key_aborts_startup(self):
        settings = Settings(secret_key="")
        with pytest.raises(SecurityConfigurationError, match="SECRET_KEY"):
            validate_security_settings(settings)

    def test_short_secret_key_is_rejected(self):
        settings = Settings(secret_key="tooshort")
        with pytest.raises(SecurityConfigurationError):
            validate_security_settings(settings)

    def test_admin_seeding_is_refused_outside_development(self):
        settings = Settings(
            secret_key="a" * 48,
            app_env="production",
            seed_default_admin=True,
            seed_admin_password="something",
        )
        with pytest.raises(SecurityConfigurationError, match="APP_ENV=development"):
            validate_security_settings(settings)

    def test_admin_seeding_requires_a_password(self):
        # It used to seed admin123 with the password "123" unconditionally.
        settings = Settings(
            secret_key="a" * 48,
            app_env="development",
            seed_default_admin=True,
            seed_admin_password="",
        )
        with pytest.raises(SecurityConfigurationError, match="SEED_ADMIN_PASSWORD"):
            validate_security_settings(settings)


class TestDemoAccounts:
    """Demo profiles are a shortcut past the signup form, not past authentication."""

    def test_demo_seeding_is_refused_outside_development(self):
        settings = Settings(
            secret_key="a" * 48,
            app_env="production",
            seed_demo_accounts=True,
            seed_demo_password="something",
        )
        with pytest.raises(SecurityConfigurationError, match="APP_ENV=development"):
            validate_security_settings(settings)

    def test_demo_seeding_requires_a_password(self):
        settings = Settings(
            secret_key="a" * 48,
            app_env="development",
            seed_demo_accounts=True,
            seed_demo_password="",
        )
        with pytest.raises(SecurityConfigurationError, match="SEED_DEMO_PASSWORD"):
            validate_security_settings(settings)

    @pytest.mark.asyncio
    async def test_no_accounts_are_offered_when_seeding_is_off(self, client):
        # The endpoint hands the browser a working password, so it must stay
        # dark unless demo accounts were deliberately switched on.
        response = await client.get("/api/v1/auth/demo-accounts")
        assert response.status_code == 200
        assert response.json()["accounts"] == []
