import uuid
import json
from unittest.mock import patch, Mock
from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from rest_framework.test import APITestCase
from rest_framework import status
from PIL import Image

from captcha.services import CaptchaService
from captcha.generator import CaptchaGenerator


class CaptchaServiceTests(TestCase):
    """Test cases for CaptchaService"""
    
    def setUp(self):
        """Clear cache before each test"""
        cache.clear()
    
    def tearDown(self):
        """Clear cache after each test"""
        cache.clear()
    
    def test_generate_key(self):
        """Test key generation returns valid UUID"""
        key = CaptchaService.generate_key()
        # Should be able to parse as UUID
        uuid.UUID(key)
        self.assertIsInstance(key, str)
    
    def test_store_captcha_data(self):
        """Test storing captcha data in cache"""
        key = "test-key-123"
        response = "ABC123"
        
        result = CaptchaService.store_captcha_data(key, response)
        
        self.assertTrue(result)
        # Verify data is stored
        stored_data = CaptchaService.fetch_captcha_data(key)
        self.assertIsNotNone(stored_data)
        self.assertEqual(stored_data['response'], 'ABC123')
        self.assertEqual(stored_data['challenge'], 'local image challenge')
        self.assertFalse(stored_data['is_used'])
    
    def test_fetch_captcha_data_not_found(self):
        """Test fetching non-existent captcha data"""
        result = CaptchaService.fetch_captcha_data("non-existent-key")
        self.assertIsNone(result)
    
    def test_validate_captcha_correct_response(self):
        """Test successful captcha validation"""
        key = "test-key-123"
        response = "ABC123"
        CaptchaService.store_captcha_data(key, response)
        
        is_valid, message = CaptchaService.validate_captcha(key, "abc123")  # Case insensitive
        
        self.assertTrue(is_valid)
        self.assertEqual(message, "کپچا معتبر است")
    
    def test_validate_captcha_wrong_response(self):
        """Test captcha validation with wrong response"""
        key = "test-key-123"
        response = "ABC123"
        CaptchaService.store_captcha_data(key, response)
        
        is_valid, message = CaptchaService.validate_captcha(key, "XYZ789")
        
        self.assertFalse(is_valid)
        self.assertEqual(message, "پاسخ کپچا نادرست است")
    
    def test_validate_captcha_expired_or_invalid_key(self):
        """Test validation with invalid/expired key"""
        is_valid, message = CaptchaService.validate_captcha("invalid-key", "ABC123")
        
        self.assertFalse(is_valid)
        self.assertEqual(message, "کپچا نامعتبر یا منقضی شده است")
    
    def test_validate_captcha_already_used(self):
        """Test validation with already used captcha"""
        key = "test-key-123"
        response = "ABC123"
        CaptchaService.store_captcha_data(key, response)
        CaptchaService.mark_as_used(key)
        
        is_valid, message = CaptchaService.validate_captcha(key, "ABC123")
        
        self.assertFalse(is_valid)
        self.assertEqual(message, "این کپچا قبلاً استفاده شده است")
    
    def test_mark_as_used(self):
        """Test marking captcha as used"""
        key = "test-key-123"
        response = "ABC123"
        CaptchaService.store_captcha_data(key, response)
        
        result = CaptchaService.mark_as_used(key)
        
        self.assertTrue(result)
        data = CaptchaService.fetch_captcha_data(key)
        self.assertTrue(data['is_used'])
    
    def test_delete_captcha(self):
        """Test deleting captcha data"""
        key = "test-key-123"
        response = "ABC123"
        CaptchaService.store_captcha_data(key, response)
        
        result = CaptchaService.delete_captcha(key)
        
        self.assertTrue(result)
        self.assertIsNone(CaptchaService.fetch_captcha_data(key))


class CaptchaGeneratorTests(TestCase):
    """Test cases for CaptchaGenerator"""
    
    def setUp(self):
        self.generator = CaptchaGenerator()
    
    def test_generate_text_length(self):
        """Test generated text has correct length"""
        text = self.generator.generate_text()
        self.assertEqual(len(text), 5)
    
    def test_generate_text_characters(self):
        """Test generated text contains only valid characters"""
        valid_chars = 'A2B9C4D8E6F7G8H6J3K5L5M4N7P3Q9R2S3TUVW4X2YZA'
        text = self.generator.generate_text()
        
        for char in text:
            self.assertIn(char, valid_chars)
    
    def test_generate_image_returns_pil_image(self):
        """Test image generation returns PIL Image"""
        text = "ABC123"
        image = self.generator.generate_image(text)
        
        self.assertIsInstance(image, Image.Image)
        self.assertEqual(image.size, (200, 80))  # Expected dimensions
    
    def test_image_to_base64(self):
        """Test image to base64 conversion"""
        text = "ABC123"
        image = self.generator.generate_image(text)
        base64_str = self.generator.image_to_base64(image)
        
        self.assertIsInstance(base64_str, str)
        self.assertTrue(len(base64_str) > 0)
        # Base64 string should be valid
        import base64
        try:
            base64.b64decode(base64_str)
        except Exception:
            self.fail("Invalid base64 string generated")


class CaptchaAPITests(APITestCase):
    """Test cases for CAPTCHA API endpoints"""

    """
    What Happens During the Test

    1- Test starts
    2- @patch replaces the real methods with fake ones
    3- We tell the fake methods what to return
    4- Our API endpoint runs, but calls the fake methods instead of real ones
    5- We check that the API response has the right structure
    6- Test ends, real methods are restored

    Exp:
    @patch('<every where see this function>')
    def test_captcha_refresh_new_generation_fails(self, <give it to here>):
    <i control what return by my self>.return_value = False
    """
    
    def setUp(self):
        cache.clear()
        # Assume your URLs are named 'captcha:generate' and 'captcha:refresh'
        self.generate_url = '/api/captcha/generate/'  # Adjust to your actual URL
        self.refresh_url = '/api/captcha/refresh/'    # Adjust to your actual URL
    
    def tearDown(self):
        cache.clear()
    
    @patch('captcha.generator.CaptchaGenerator.generate_text')
    @patch('captcha.generator.CaptchaGenerator.generate_image')
    @patch('captcha.generator.CaptchaGenerator.image_to_base64')
    # During this test, whenever CaptchaGenerator.generate_text() is called, don't run the real method. Instead, use a fake version that I control.
    # Notice the order: the patches are applied bottom-to-top, so the method parameters are in reverse order of the decorators.
    def test_captcha_generate_success(self, mock_base64, mock_image, mock_text):
        """Test successful captcha generation"""
        mock_text.return_value = "ABC123" #When generate_text() is called, return 'ABC123' instead of generating random text.
        mock_image.return_value = Mock(spec=Image.Image)
        mock_base64.return_value = "fake_base64_data"
        
        response = self.client.get(self.generate_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('key', data)
        self.assertIn('image_data', data)
        self.assertIn('expires_in', data)
        self.assertTrue(data['image_data'].startswith('data:image/png;base64,'))
        
        # Verify UUID format
        uuid.UUID(data['key'])
    
    @patch('captcha.services.CaptchaService.store_captcha_data')
    # During this test, whenever CaptchaGenerator.generate_text() is called, don't run the real method. Instead, use a fake version that I control.
    # Notice the order: the patches are applied bottom-to-top, so the method parameters are in reverse order of the decorators.
    def test_captcha_generate_storage_failure(self, mock_store):
        """Test captcha generation when storage fails"""
        mock_store.return_value = False
        
        response = self.client.get(self.generate_url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('خطا در ایجاد کپچا', response.json()['detail'])
    
    def test_captcha_refresh_missing_old_captcha(self):
        """Test refresh without providing old_captcha parameter"""
        response = self.client.get(self.refresh_url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('آیدی کپچا قبلی وارد نشده است', response.json()['detail'])
    
    def test_captcha_refresh_invalid_uuid(self):
        """Test refresh with invalid UUID format"""
        response = self.client.get(self.refresh_url, {'old_captcha': 'invalid-uuid'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('فرمت آیدی کپچا نامعتبر است', response.json()['detail'])
    
    def test_captcha_refresh_nonexistent_captcha(self):
        """Test refresh with non-existent captcha"""
        fake_uuid = str(uuid.uuid4())
        response = self.client.get(self.refresh_url, {'old_captcha': fake_uuid})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('کپچا قبلی معتبر نیست', response.json()['detail'])
    
    def test_captcha_refresh_already_used(self):
        """Test refresh with already used captcha"""
        # Create and use a captcha
        key = CaptchaService.generate_key()
        CaptchaService.store_captcha_data(key, "ABC123")
        CaptchaService.mark_as_used(key)
        
        response = self.client.get(self.refresh_url, {'old_captcha': key})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('کپچا قبلی معتبر نیست', response.json()['detail'])
    
    @patch('captcha.generator.CaptchaGenerator.generate_text')
    @patch('captcha.generator.CaptchaGenerator.generate_image')
    @patch('captcha.generator.CaptchaGenerator.image_to_base64')
    # During this test, whenever CaptchaGenerator.generate_text() is called, don't run the real method. Instead, use a fake version that I control.
    # Notice the order: the patches are applied bottom-to-top, so the method parameters are in reverse order of the decorators.
    def test_captcha_refresh_success(self, mock_base64, mock_image, mock_text):
        """Test successful captcha refresh"""
        # Create a valid old captcha
        old_key = CaptchaService.generate_key()
        CaptchaService.store_captcha_data(old_key, "ABC123")
        
        # Mock new captcha generation
        mock_text.return_value = "XYZ789" 
        mock_image.return_value = Mock(spec=Image.Image)
        mock_base64.return_value = "new_fake_base64_data"
        
        response = self.client.get(self.refresh_url, {'old_captcha': old_key})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('key', data)
        self.assertIn('image_data', data)
        self.assertIn('expires_in', data)
        
        # Verify new key is different from old key
        self.assertNotEqual(data['key'], old_key)
        
        # Verify old captcha is marked as used
        old_data = CaptchaService.fetch_captcha_data(old_key)
        self.assertTrue(old_data['is_used'])
    
    def test_captcha_refresh_new_generation_fails(self):
        """Test that old captcha remains valid when new generation fails"""
        # Create a valid old captcha
        old_key = CaptchaService.generate_key()
        CaptchaService.store_captcha_data(old_key, "ABC123")  # real call
        
        with patch('captcha.services.CaptchaService.store_captcha_data') as mock_store:
            mock_store.return_value = False # Mock storage failure for new captcha
            #run this view and whenever react the function store_captcha_data mock it to return false !
            response = self.client.get(self.refresh_url, {'old_captcha': old_key})
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

            old_data = CaptchaService.fetch_captcha_data(old_key)
            self.assertFalse(old_data['is_used'])

class CaptchaIntegrationTests(APITestCase):
    """Integration tests for complete CAPTCHA flow"""
    
    def setUp(self):
        cache.clear()
        self.generate_url = '/api/captcha/generate/'
        self.refresh_url = '/api/captcha/refresh/'
    
    def tearDown(self):
        cache.clear()
    
    def test_complete_captcha_flow(self):
        """Test complete flow: generate -> validate -> refresh"""
        # 1. Generate captcha
        response = self.client.get(self.generate_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        captcha_key = response.json()['key']
        
        # 2. Validate we can fetch the data
        captcha_data = CaptchaService.fetch_captcha_data(captcha_key)
        self.assertIsNotNone(captcha_data)
        self.assertFalse(captcha_data['is_used'])
        
        # 3. Validate captcha
        is_valid, _ = CaptchaService.validate_captcha(
            captcha_key, 
            captcha_data['response']
        )
        self.assertTrue(is_valid)
        
        # 4. Verify captcha is marked as used
        updated_data = CaptchaService.fetch_captcha_data(captcha_key)
        self.assertTrue(updated_data['is_used'])
        
        # 5. Try to validate again (should fail)
        is_valid, message = CaptchaService.validate_captcha(
            captcha_key, 
            captcha_data['response']
        )
        self.assertFalse(is_valid)
        self.assertIn('قبلاً استفاده شده', message)