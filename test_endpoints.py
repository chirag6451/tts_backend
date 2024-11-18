#!/usr/bin/env python3
import subprocess
import json
import time
from datetime import datetime

class APITester:
    def __init__(self):
        self.base_url = "http://localhost:8000"  # Updated port to 8000
        self.token = None
        self.user_id = None
        self.task_id = None
        self.test_user = {
            "email": f"test_{int(time.time())}@example.com",
            "password": "testpassword123"
        }
        self.debug = True

    def run_curl(self, method, endpoint, data=None, files=None, auth=False, form_data=False):
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        
        curl_command = ["curl", "-L", "-X", method, f"{self.base_url}{endpoint}"]
        
        if auth and self.token:
            curl_command.extend(["-H", f"Authorization: Bearer {self.token}"])
        
        if data:
            if form_data:
                for key, value in data.items():
                    curl_command.extend(["-F", f"{key}={value}"])
            else:
                curl_command.extend(["-H", "Content-Type: application/json"])
                curl_command.extend(["-d", json.dumps(data)])
        
        if files:
            for key, filepath in files.items():
                curl_command.extend(["-F", f"{key}=@{filepath}"])

        if self.debug:
            print(f"\nExecuting: {' '.join(curl_command)}")

        try:
            result = subprocess.run(curl_command, capture_output=True, text=True)
            if self.debug:
                print(f"Response: {result.stdout}")
                if result.stderr:
                    print(f"Error: {result.stderr}")
            return json.loads(result.stdout) if result.stdout else None
        except json.JSONDecodeError:
            print(f"Failed to parse response: {result.stdout}")
            return None
        except Exception as e:
            print(f"Error: {str(e)}")
            return None

    def test_registration(self):
        print("\nTesting User Registration...")
        response = self.run_curl(
            "POST",
            "/auth/register",
            data=self.test_user
        )
        
        if response and "id" in response:
            print("Registration successful")
            return True
        else:
            print("Test failed: Registration failed")
            return False

    def test_login(self):
        print("\nTesting User Login...")
        login_data = {
            "username": self.test_user["email"],
            "password": self.test_user["password"],
            "grant_type": "password"
        }
        
        response = self.run_curl(
            "POST",
            "/auth/login",
            data=login_data,
            form_data=True
        )
        
        if response and "access_token" in response:
            self.token = response["access_token"]
            self.user_id = response["user_id"]
            print("Login successful")
            return True
        else:
            print("Test failed: Login failed")
            return False

    def test_create_task(self):
        print("\nTesting Task Creation...")
        task_data = {
            "title": "Test Task",
            "description": "This is a test task",
            "audio_file": "@test_audio.m4a"
        }
        
        # Create a test audio file
        with open("test_audio.m4a", "w") as f:
            f.write("Test audio content")
        
        response = self.run_curl(
            "POST",
            "/tasks",
            data=task_data,
            auth=True,
            form_data=True
        )
        
        if response and "id" in response:
            self.task_id = response["id"]
            print("Task created successfully")
            return True
        else:
            print("Test failed: Task creation failed")
            return False

    def test_get_tasks(self):
        print("\nTesting Get All Tasks...")
        response = self.run_curl(
            "GET",
            "/tasks",
            auth=True
        )
        
        if response and isinstance(response, list):
            print("Successfully retrieved tasks")
            return True
        else:
            print("Test failed: Get tasks failed")
            return False

    def test_get_task(self):
        print("\nTesting Get Single Task...")
        if not self.task_id:
            print("No task ID available for testing")
            return False
            
        response = self.run_curl(
            "GET",
            f"/tasks/{self.task_id}",
            auth=True
        )
        
        if response and "id" in response:
            print("Task retrieved successfully")
            return True
        else:
            print("Test failed: Get task failed")
            return False

    def test_update_task(self):
        print("\nTesting Task Update...")
        if not self.task_id:
            print("No task ID available for testing")
            return False
            
        update_data = {
            "title": "Updated Test Task",
            "description": "This task has been updated"
        }
        
        response = self.run_curl(
            "PUT",
            f"/tasks/{self.task_id}",
            data=update_data,
            auth=True
        )
        
        if response and "id" in response:
            print("Task updated successfully")
            return True
        else:
            print("Test failed: Task update failed")
            return False

    def test_delete_task(self):
        print("\nTesting Task Deletion...")
        if not self.task_id:
            print("No task ID available for testing")
            return False
            
        response = self.run_curl(
            "DELETE",
            f"/tasks/{self.task_id}",
            auth=True
        )
        
        if response and "message" in response:
            print("Task deleted successfully")
            return True
        else:
            print("Test failed: Task deletion failed")
            return False

    def run_all_tests(self):
        print("\nStarting API Tests...")
        print("=" * 50)
        
        tests = [
            self.test_registration,
            self.test_login,
            self.test_create_task,
            self.test_get_tasks,
            self.test_get_task,
            self.test_update_task,
            self.test_delete_task
        ]
        
        results = []
        for test in tests:
            result = test()
            results.append(result)
        
        print("\n" + "=" * 50)
        print("Test Results Summary")
        print("=" * 50)
        print(f"Total Tests: {len(results)}")
        print(f"Passed: {results.count(True)}")
        print(f"Failed: {results.count(False)}")
        print("=" * 50)
        
        return all(results)

def main():
    tester = APITester()
    success = tester.run_all_tests()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()
