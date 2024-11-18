import requests
import unittest
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestAuthAPI(unittest.TestCase):
    BASE_URL = "http://localhost:8000"
    
    def setUp(self):
        """Setup test case"""
        self.test_user = {
            "email": "test@example.com",
            "password": "test123456"
        }
        # Clean up: Try to delete test user if exists
        self._cleanup_test_user()

    def _cleanup_test_user(self):
        """Helper method to clean up test user"""
        try:
            # You might need to implement a delete user endpoint for this
            pass
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    def test_1_register(self):
        """Test user registration"""
        logger.info("Testing registration...")
        
        url = f"{self.BASE_URL}/auth/register"
        response = requests.post(
            url,
            json=self.test_user,
            headers={"Content-Type": "application/json"}
        )
        
        logger.info(f"Registration Response: {response.status_code} - {response.text}")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["user_id"])

    def test_2_login(self):
        """Test user login"""
        logger.info("Testing login...")
        
        # First register the user
        self.test_1_register()
        
        # Now try to login
        url = f"{self.BASE_URL}/auth/login"
        response = requests.post(
            url,
            json=self.test_user,
            headers={"Content-Type": "application/json"}
        )
        
        logger.info(f"Login Response: {response.status_code} - {response.text}")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("token_type", data)
        self.assertEqual(data["token_type"], "bearer")

    def test_3_invalid_login(self):
        """Test login with invalid credentials"""
        logger.info("Testing invalid login...")
        
        invalid_login = {
            "email": self.test_user["email"],
            "password": "wrongpassword"
        }
        
        url = f"{self.BASE_URL}/auth/login"
        response = requests.post(
            url,
            json=invalid_login,
            headers={"Content-Type": "application/json"}
        )
        
        logger.info(f"Invalid Login Response: {response.status_code} - {response.text}")
        self.assertEqual(response.status_code, 401)

    def test_4_duplicate_registration(self):
        """Test registering with existing email"""
        logger.info("Testing duplicate registration...")
        
        # First register the user
        self.test_1_register()
        
        # Try to register again with the same email
        url = f"{self.BASE_URL}/auth/register"
        response = requests.post(
            url,
            json=self.test_user,
            headers={"Content-Type": "application/json"}
        )
        
        logger.info(f"Duplicate Registration Response: {response.status_code} - {response.text}")
        self.assertEqual(response.status_code, 400)

if __name__ == "__main__":
    unittest.main(verbosity=2)
