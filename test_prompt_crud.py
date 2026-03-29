#!/usr/bin/env python3
"""
Automatic test script for Prompt CRUD API endpoints.
Run with: python test_prompt_crud.py
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import httpx
import config
from prompts import Promptset

# Test configuration
BASE_URL = "http://127.0.0.1:8080"
API_BASE = f"{BASE_URL}/api/prompts"

class PromptCRUDTest:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.created_ids = []
        
    async def setup(self):
        """Setup before tests"""
        print("=== Prompt CRUD Test Suite ===")
        
    async def cleanup(self):
        """Cleanup after tests"""
        # Delete all created prompts
        for prompt_id in self.created_ids:
            try:
                await self.client.delete(f"{API_BASE}/{prompt_id}")
            except:
                pass
        
        await self.client.aclose()
        print("\n=== Test Cleanup Complete ===")
    
    async def test_list_prompts(self):
        """Test GET /api/prompts"""
        print("\n1. Testing LIST prompts...")
        try:
            response = await self.client.get(API_BASE)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            prompts = response.json()
            print(f"   ✓ Got {len(prompts)} prompts")
            return prompts
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_create_prompt(self):
        """Test POST /api/prompts"""
        print("\n2. Testing CREATE prompt...")
        new_prompt = {
            "system_message": "Test System Prompt",
            "prePrompt": "Test Pre Prompt",
            "postPrompt": "Test Post Prompt",
            "infostr": "Test info string",
            "allowLongAnswer": True,
            "temperature": 0.5,
            "top_p": 0.9,
            "maxNewToken": 1000,
            "targetlanguage": "EN",
            "AIasJudge": True
        }
        
        try:
            response = await self.client.post(API_BASE, json=new_prompt)
            assert response.status_code == 201, f"Expected 201, got {response.status_code}"
            created = response.json()
            assert created["system_message"] == new_prompt["system_message"]
            assert created["PromptID"] is not None
            print(f"   ✓ Created prompt ID {created['PromptID']}")
            self.created_ids.append(created["PromptID"])
            return created
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_get_prompt(self, prompt_id):
        """Test GET /api/prompts/{id}"""
        print(f"\n3. Testing GET prompt {prompt_id}...")
        try:
            response = await self.client.get(f"{API_BASE}/{prompt_id}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            prompt = response.json()
            assert prompt["PromptID"] == prompt_id
            print(f"   ✓ Retrieved prompt {prompt_id}")
            return prompt
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_update_prompt(self, prompt_id):
        """Test PUT /api/prompts/{id}"""
        print(f"\n4. Testing UPDATE prompt {prompt_id}...")
        update_data = {
            "system_message": "Updated System Prompt",
            "temperature": 0.7,
            "targetlanguage": "FR",
            "AIasJudge": False
        }
        
        try:
            response = await self.client.put(f"{API_BASE}/{prompt_id}", json=update_data)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            updated = response.json()
            assert updated["system_message"] == update_data["system_message"]
            assert updated["temperature"] == update_data["temperature"]
            assert updated["targetlanguage"] == update_data["targetlanguage"]
            assert updated["AIasJudge"] == update_data["AIasJudge"]
            print(f"   ✓ Updated prompt {prompt_id}")
            return updated
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_delete_prompt(self, prompt_id):
        """Test DELETE /api/prompts/{id}"""
        print(f"\n5. Testing DELETE prompt {prompt_id}...")
        try:
            # First verify it exists
            get_response = await self.client.get(f"{API_BASE}/{prompt_id}")
            assert get_response.status_code == 200
            
            # Then delete it
            delete_response = await self.client.delete(f"{API_BASE}/{prompt_id}")
            assert delete_response.status_code == 204, f"Expected 204, got {delete_response.status_code}"
            
            # Verify it's gone
            get_after_response = await self.client.get(f"{API_BASE}/{prompt_id}")
            assert get_after_response.status_code == 404, f"Expected 404 after deletion, got {get_after_response.status_code}"
            
            print(f"   ✓ Deleted prompt {prompt_id}")
            self.created_ids.remove(prompt_id)
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_error_cases(self):
        """Test error cases"""
        print("\n6. Testing error cases...")
        
        # Test GET non-existent prompt
        try:
            response = await self.client.get(f"{API_BASE}/999999")
            assert response.status_code == 404, f"Expected 404 for non-existent prompt, got {response.status_code}"
            print("   ✓ GET non-existent prompt returns 404")
        except Exception as e:
            print(f"   ✗ GET error test failed: {e}")
            raise
        
        # Test DELETE non-existent prompt
        try:
            response = await self.client.delete(f"{API_BASE}/999999")
            assert response.status_code == 404, f"Expected 404 for non-existent prompt, got {response.status_code}"
            print("   ✓ DELETE non-existent prompt returns 404")
        except Exception as e:
            print(f"   ✗ DELETE error test failed: {e}")
            raise
        
        # Test invalid data (missing required field)
        try:
            invalid_data = {
                "prePrompt": "Only prePrompt, missing system_message"
            }
            response = await self.client.post(API_BASE, json=invalid_data)
            # FastAPI validation should return 422
            assert response.status_code == 422, f"Expected 422 for invalid data, got {response.status_code}"
            print("   ✓ Invalid data returns validation error")
        except Exception as e:
            print(f"   ✗ Validation test failed: {e}")
            raise
    
    async def run_all_tests(self):
        """Run all tests"""
        try:
            await self.setup()
            
            # Test 1: List prompts
            initial_prompts = await self.test_list_prompts()
            
            # Test 2: Create prompt
            created = await self.test_create_prompt()
            created_id = created["PromptID"]
            
            # Test 3: Get created prompt
            await self.test_get_prompt(created_id)
            
            # Test 4: Update prompt
            await self.test_update_prompt(created_id)
            
            # Test 5: Verify update
            updated = await self.test_get_prompt(created_id)
            assert updated["system_message"] == "Updated System Prompt"
            
            # Test 6: Error cases
            await self.test_error_cases()
            
            # Test 7: Delete prompt (clean up)
            await self.test_delete_prompt(created_id)
            
            # Final list to verify deletion
            final_prompts = await self.test_list_prompts()
            
            print(f"\n=== All Tests Passed! ===")
            print(f"Initial prompts: {len(initial_prompts)}")
            print(f"Final prompts: {len(final_prompts)}")
            
        except Exception as e:
            print(f"\n=== Test Failed: {e} ===")
            raise
        finally:
            await self.cleanup()

async def main():
    """Main entry point"""
    # Check if server is running
    print("Checking if server is running...")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/")
            if response.status_code != 200:
                print(f"Warning: Server returned status {response.status_code}")
                print("Make sure the server is running with: python gui3.py")
                print("or: uvicorn gui3:app --host 0.0.0.0 --port 8080")
                return
    except httpx.ConnectError:
        print("Error: Could not connect to server at", BASE_URL)
        print("Make sure the server is running with: python gui3.py")
        print("or: uvicorn gui3:app --host 0.0.0.0 --port 8080")
        return
    
    # Run tests
    tester = PromptCRUDTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    # Make sure we're in the right environment
    print("Python executable:", sys.executable)
    print("Working directory:", os.getcwd())
    
    # Run async tests
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)