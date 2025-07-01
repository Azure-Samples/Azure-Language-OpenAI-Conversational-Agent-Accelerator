import asyncio
import time
import subprocess
import requests
import json
import sys
from threading import Thread
import signal
import os

# Test cases
TEST_CASES = [
    {
        "name": "order_status_single_utterance",
        "input": "What's the status of order 12345?",
        "expected_response": ["Order 12345 is shipped and will arrive in 2-3 days."]
    },
    {
        "name": "order_refund_single_utterance",
        "input": "I want to check on my refund for order 0984?",
        "expected_response": ["Refund for order 0984 has been processed successfully."]
    },
    {
        "name": "order_cancel_single_utterance",
        "input": "Cancel my order 56789?",
        "expected_response": ["Cancellation for order 56789 has been processed successfully."]
    },
    {
        "name": "multiple_utterances",
        "input": "What's the status of order 0913280918409? Please cancel my order 62346?",
        "expected_response": [
            "Order 0913280918409 is shipped and will arrive in 2-3 days.",
            "Cancellation for order 62346 has been processed successfully."
        ]
    },
    {
        "name": "return policy",
        "input": "What is the return policy",
        "expected_response": [
            "Contoso Outdoors is proud to offer a 30 day refund policy. Return unopened, unused products within 30 days of purchase to any Contoso Outdoors store for a full refund."
        ]
    }
    # add more example utterances for testing when there's not enough information
]

class AppTester:
    def __init__(self, host="localhost", port=8000):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.process = None
        
    def start_app(self):
        """Start the FastAPI app using uvicorn"""
        print("Starting FastAPI app...")
        env = os.environ.copy()
        env["PYTHONPATH"] = "src"
        
        self.process = subprocess.Popen([
            "uvicorn", "app:app", 
            "--host", self.host, 
            "--port", str(self.port),
            "--reload"
        ], env=env, cwd=".")
        
        # Wait for app to start
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get(f"{self.base_url}/")
                if response.status_code in [200, 404]:  # 404 is fine, means server is running
                    print(f"App started successfully on {self.base_url}")
                    return True
            except requests.ConnectionError:
                time.sleep(1)
                
        raise Exception("Failed to start app")
    
    def stop_app(self):
        """Stop the FastAPI app"""
        if self.process:
            print("Stopping FastAPI app...")
            self.process.terminate()
            self.process.wait()
    
    def test_chat(self, message):
        """Send a chat message and return the response"""
        try:
            # 
            response = requests.post(
                f"{self.base_url}/chat",
                json={"message": message},
                timeout=180  # 180 second timeout
            )
            return response
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return None
    
    def run_tests(self):
        """Run all test cases"""
        results = []
        
        for i, test_case in enumerate(TEST_CASES):
            print(f"\n{'='*50}")
            print(f"Test {i+1}/{len(TEST_CASES)}: {test_case['name']}")
            print(f"Input: {test_case['input']}")
            
            start_time = time.time()
            response = self.test_chat(test_case['input'])
            end_time = time.time()
            
            processing_time = end_time - start_time
            print(f"Processing time: {processing_time:.2f} seconds")
            
            if response is None:
                print("❌ FAILED: No response received")
                results.append(False)
                continue
                
            if response.status_code != 200:
                print(f"❌ FAILED: Status code {response.status_code}")
                print(f"Response: {response.text}")
                results.append(False)
                continue
            
            try:
                data = response.json()
                messages = data.get("messages", [])
                print(f"Response: {messages}")
                print(f"Expected: {test_case['expected_response']}")
                
                # Direct assertion check
                try:
                    assert messages == test_case['expected_response'], f"Expected {test_case['expected_response']}, got {messages}"
                    print("✅ PASSED: Response matches expected exactly")
                    results.append(True)
                except AssertionError as e:
                    print(f"❌ FAILED: {str(e)}")
                    results.append(False)
                    
            except json.JSONDecodeError:
                print("❌ FAILED: Invalid JSON response")
                results.append(False)
        
        return results
    
    def print_summary(self, results):
        """Print test summary"""
        passed = sum(results)
        total = len(results)
        
        print(f"\n{'='*50}")
        print("TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Passed: {passed}/{total}")
        print(f"Failed: {total - passed}/{total}")
        
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print("❌ Some tests failed")
            
        return passed == total

def main():
    """Main test function"""
    tester = AppTester()
    
    try:
        # Start the app
        tester.start_app()
        
        # Run tests
        results = tester.run_tests()
        
        # Print summary
        success = tester.print_summary(results)
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)
    finally:
        tester.stop_app()

if __name__ == "__main__":
    main()