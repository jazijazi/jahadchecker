from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from accounts.tokenization import create_access_token,create_refresh_token

User = get_user_model()


class RegisterUserTests(APITestCase):
    def setUp(self):
        self.url = reverse('accounts:register')

        self.valid_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "StrongP@ssw0rd",
            "confirm_password": "StrongP@ssw0rd",
            "first_name": "Ali",
            "last_name": "Rezaei",
            "first_name_fa": "علی",
            "last_name_fa": "رضایی",
            "address": "Tehran"
        }

    def test_successful_registration(self):
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('detail', response.data)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_passwords_do_not_match(self):
        data = self.valid_data.copy()
        data["confirm_password"] = "WrongPassword1!"
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)

    def test_weak_password_fails(self):
        data = self.valid_data.copy()
        data["password"] = "weakpass"
        data["confirm_password"] = "weakpass"
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_weak_password_fails2(self):
        data = self.valid_data.copy()
        data["password"] = "123456789"
        data["confirm_password"] = "123456789"
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_weak_password_fails3(self):
        data = self.valid_data.copy()
        data["password"] = "A44444444B$"
        data["confirm_password"] = "A44444444B$"
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_username_already_exists(self):
        User.objects.create_user(username=f"{self.valid_data['username']}", password="SomeP@ss123")
        response = self.client.post(self.url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)

    def test_missing_required_fields(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertIn("password", response.data)

class ProfileUserTests(APITestCase):
    def setUp(self):
        self.url = reverse('accounts:userprofile')
        self.username = 'testuser'
        self.password = 'testpass123'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.access_token = create_access_token(user_id=self.user.id , expires_in_seconds=90)

    def test_get_userprofile_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.get(self.url)
        self.assertIn('username', response.data)
        self.assertIn('first_name', response.data)
        self.assertIn('last_name', response.data)

    def test_get_userprofile_without_authenticate(self):
        response = self.client.get(self.url)
        self.assertIn('detail', response.data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class EditProfileUserTests(APITestCase):
    def setUp(self):
        self.url = reverse('accounts:userprofile')
        self.valid_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "StrongP@ssw0rd",
            "first_name": "Ali",
            "last_name": "Rezaei",
            "first_name_fa": "علی",
            "last_name_fa": "رضایی",
            "address": "Tehran"
        }
        self.user = User.objects.create_user(**self.valid_data)
        self.access_token = create_access_token(user_id=self.user.id , expires_in_seconds=90)

    def test_update_userprofile_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        self.valid_data["first_name"] = "newfirstname"
        response = self.client.put(self.url , self.valid_data)
        self.assertIn("email" , response.data)
        self.assertIn("first_name" , response.data)
        self.assertEqual(response.data["first_name"] , self.valid_data["first_name"])
        self.assertEqual(response.data["email"] , self.valid_data["email"])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        

    def test_update_userprofile_without_authenticate(self):
        response = self.client.post(self.url,self.valid_data)
        self.assertIn('detail', response.data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)