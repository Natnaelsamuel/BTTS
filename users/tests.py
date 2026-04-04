from rest_framework import status
from rest_framework.test import APITestCase

from .models import User, UserRole


class AuthenticationAPITests(APITestCase):
    def test_register_api_creates_user(self):
        payload = {
            "username": "passenger001",
            "email": "passenger@example.com",
            "password": "strongPass123",
            "first_name": "Jane",
            "last_name": "Doe",
            "role": UserRole.PASSENGER,
        }

        response = self.client.post(
            "/api/auth/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="passenger001").exists())

    def test_register_api_blocks_admin_role(self):
        payload = {
            "username": "admin001",
            "email": "admin@example.com",
            "password": "strongPass123",
            "role": UserRole.ADMIN,
        }

        response = self.client.post(
            "/api/auth/register/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", response.data)

    def test_login_api_returns_jwt_tokens_and_user_payload(self):
        User.objects.create_user(
            username="driver001", email="driver001@example.com", password="strongPass123", role=UserRole.DRIVER)

        response = self.client.post(
            "/api/auth/login/",
            {"username": "driver001", "password": "strongPass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["role"], UserRole.DRIVER)

    def test_login_api_accepts_email(self):
        User.objects.create_user(
            username="driver004", email="driver004@example.com", password="strongPass123", role=UserRole.DRIVER)

        response = self.client.post(
            "/api/auth/login/",
            {"email": "driver004@example.com", "password": "strongPass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["username"], "driver004")

    def test_me_endpoint_requires_authentication(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_returns_current_user(self):
        user = User.objects.create_user(
            username="passenger002", email="passenger002@example.com", password="strongPass123", role=UserRole.PASSENGER)
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "passenger002")
        self.assertEqual(response.data["role"], UserRole.PASSENGER)

    def test_admin_permission_allows_admin_only(self):
        admin_user = User.objects.create_user(
            username="admin002", email="admin002@example.com", password="strongPass123", role=UserRole.ADMIN)
        driver_user = User.objects.create_user(
            username="driver002", email="driver002@example.com", password="strongPass123", role=UserRole.DRIVER)

        self.client.force_authenticate(user=driver_user)
        denied_response = self.client.get("/api/auth/admin-check/")
        self.assertEqual(denied_response.status_code,
                         status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=admin_user)
        allowed_response = self.client.get("/api/auth/admin-check/")
        self.assertEqual(allowed_response.status_code, status.HTTP_200_OK)

    def test_driver_permission_allows_driver_only(self):
        admin_user = User.objects.create_user(
            username="admin003", email="admin003@example.com", password="strongPass123", role=UserRole.ADMIN)
        driver_user = User.objects.create_user(
            username="driver003", email="driver003@example.com", password="strongPass123", role=UserRole.DRIVER)

        self.client.force_authenticate(user=admin_user)
        denied_response = self.client.get("/api/auth/driver-check/")
        self.assertEqual(denied_response.status_code,
                         status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=driver_user)
        allowed_response = self.client.get("/api/auth/driver-check/")
        self.assertEqual(allowed_response.status_code, status.HTTP_200_OK)
