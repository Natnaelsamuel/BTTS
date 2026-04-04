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

    def test_admin_can_list_users(self):
        admin_user = User.objects.create_user(
            username="admin_list",
            email="admin_list@example.com",
            password="strongPass123",
            role=UserRole.ADMIN,
        )
        User.objects.create_user(
            username="passenger_list",
            email="passenger_list@example.com",
            password="strongPass123",
            role=UserRole.PASSENGER,
        )

        self.client.force_authenticate(user=admin_user)
        response = self.client.get("/api/auth/users/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 2)

    def test_admin_can_search_users(self):
        admin_user = User.objects.create_user(
            username="admin_search",
            email="admin_search@example.com",
            password="strongPass123",
            role=UserRole.ADMIN,
        )
        User.objects.create_user(
            username="driver_search",
            email="driver_search@example.com",
            password="strongPass123",
            first_name="John",
            role=UserRole.DRIVER,
        )
        User.objects.create_user(
            username="passenger_search",
            email="passenger_search@example.com",
            password="strongPass123",
            first_name="Jane",
            role=UserRole.PASSENGER,
        )

        self.client.force_authenticate(user=admin_user)
        response = self.client.get("/api/auth/users/search/?q=driver")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [item["username"] for item in response.data]
        self.assertIn("driver_search", usernames)
        self.assertNotIn("passenger_search", usernames)

    def test_non_admin_cannot_list_or_search_users(self):
        passenger = User.objects.create_user(
            username="passenger_denied",
            email="passenger_denied@example.com",
            password="strongPass123",
            role=UserRole.PASSENGER,
        )

        self.client.force_authenticate(user=passenger)
        list_response = self.client.get("/api/auth/users/")
        search_response = self.client.get("/api/auth/users/search/?q=admin")

        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(search_response.status_code,
                         status.HTTP_403_FORBIDDEN)
