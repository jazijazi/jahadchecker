from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.utils.timezone import now

from accounts.tokenization import create_access_token,create_refresh_token

User = get_user_model()

class LoginUserTests(APITestCase):
    def setUp(self):
        self.username = 'testuser'
        self.password = 'testpass123'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.login_url = reverse('accounts:login')

    def test_login_success(self):
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password,
            'rememberMe': True
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], self.username)
        self.assertIn('refresh_token', response.cookies)

    def test_login_wrong_password(self):
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'نام کاربری یا رمز عبور اشتباه است')

    def test_login_missing_fields(self):
        response = self.client.post(self.login_url, {
            'username': ''
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail']['password'][0], 'رمز عبور الزامی است')

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'اکانت شما موقتاً غیرفعال شده است لطفا با پشتیبانی تماس بگیرید')

    def test_refresh_token_cookie_set(self):
        response = self.client.post(self.login_url, {
            'username': self.username,
            'password': self.password,
            'rememberMe': True
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['refresh_token']['httponly'])

class RefreshTokenTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.refresh_token = create_refresh_token(user_id=self.user.id, expires_in_days=7)
        self.refresh_url = reverse('accounts:refresh')

    def test_refresh_token_success(self):
        self.client.cookies['refresh_token'] = self.refresh_token

        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    def test_refresh_token_missing(self):
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_refresh_token_invalid(self):
        self.client.cookies['refresh_token'] = 'invalid.token.value'

        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

class LogoutTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.refresh_token = create_refresh_token(user_id=self.user.id, expires_in_days=7)
        self.access_token = create_access_token(user_id=self.user.id , expires_in_seconds=90)
        self.refresh_url = reverse('accounts:logout')
    
    def test_logout_sucess(self):
        self.client.cookies['refresh_token'] = self.refresh_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('detail', response.data)

    def test_logout_without_authenticate(self):
        self.client.cookies['refresh_token'] = self.refresh_token
        response = self.client.post(self.refresh_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)