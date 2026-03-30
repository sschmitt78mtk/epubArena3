#!/usr/bin/env python3
"""
Automatic test script for API Config CRUD API endpoints.
Run with: python test_api_configs.py
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

# Test configuration
BASE_URL = "http://127.0.0.1:8080"
API_BASE = f"{BASE_URL}/api/configs"

class APIConfigCRUDTest:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.created_ids = []
        self.original_configs = []
        
    async def setup(self):
        """Setup before tests"""
        print("=== API Config CRUD Test Suite ===")
        # Load original configs to restore later
        self.original_configs = await self.get_configs_backup()
        
    async def cleanup(self):
        """Cleanup after tests"""
        # Restore original configs
        await self.restore_configs_backup()
        
        await self.client.aclose()
        print("\n=== Test Cleanup Complete ===")
    
    async def get_configs_backup(self):
        """Get current configs for backup"""
        response = await self.client.get(API_BASE)
        return response.json()
    
    async def restore_configs_backup(self):
        """Restore original configs"""
        # Clear current configs
        current_configs = await self.get_configs_backup()
        for config_item in current_configs:
            # Skip if it was in original
            if not any(c["id"] == config_item["id"] for c in self.original_configs):
                try:
                    await self.client.delete(f"{API_BASE}/{config_item['id']}")
                except:
                    pass
        
        # Add back originals that might have been deleted
        current_after = await self.get_configs_backup()
        for original in self.original_configs:
            if not any(c["id"] == original["id"] for c in current_after):
                # Need to recreate (but we can't know original keys due to masking)
                # This is a limitation - we'll just note it
                print(f"   Note: Could not restore config {original['id']} due to key masking")
    
    async def test_list_configs(self):
        """Test GET /api/configs"""
        print("\n1. Testing LIST API configs...")
        try:
            response = await self.client.get(API_BASE)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            configs = response.json()
            print(f"   ✓ Got {len(configs)} configs")
            return configs
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_create_config(self):
        """Test POST /api/configs"""
        print("\n2. Testing CREATE API config...")
        new_config = {
            "name": "Test API Config",
            "OPENAI_API_BASE": "https://api.test.com/v1",
            "OPENAI_API_KEY": "sk-test1234567890",
            "OPEN_API_MODELNAME": "test-model",
            "modelname": "Test Model"
        }
        
        try:
            response = await self.client.post(API_BASE, json=new_config)
            assert response.status_code == 201, f"Expected 201, got {response.status_code}"
            created = response.json()
            assert created["name"] == new_config["name"]
            assert created["OPENAI_API_BASE"] == new_config["OPENAI_API_BASE"]
            assert created["OPEN_API_MODELNAME"] == new_config["OPEN_API_MODELNAME"]
            assert created["modelname"] == new_config["modelname"]
            # API key should be masked in response
            assert created["OPENAI_API_KEY"].startswith("••••••"), f"API key should be masked, got: {created['OPENAI_API_KEY']}"
            print(f"   ✓ Created config ID {created['id']} (key masked: {created['OPENAI_API_KEY'][:10]}...)")
            self.created_ids.append(created["id"])
            return created
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_get_config(self, config_id):
        """Test GET /api/configs/{id}"""
        print(f"\n3. Testing GET config {config_id}...")
        try:
            response = await self.client.get(f"{API_BASE}/{config_id}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            config_item = response.json()
            assert config_item["id"] == config_id
            print(f"   ✓ Retrieved config {config_id}")
            return config_item
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_update_config(self, config_id):
        """Test PUT /api/configs/{id}"""
        print(f"\n4. Testing UPDATE config {config_id}...")
        update_data = {
            "name": "Updated API Config",
            "OPENAI_API_BASE": "https://api.updated.com/v1",
            "OPEN_API_MODELNAME": "updated-model",
            "modelname": "Updated Model"
        }
        
        try:
            response = await self.client.put(f"{API_BASE}/{config_id}", json=update_data)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            updated = response.json()
            assert updated["name"] == update_data["name"]
            assert updated["OPENAI_API_BASE"] == update_data["OPENAI_API_BASE"]
            assert updated["OPEN_API_MODELNAME"] == update_data["OPEN_API_MODELNAME"]
            assert updated["modelname"] == update_data["modelname"]
            # API key should still be masked
            assert updated["OPENAI_API_KEY"].startswith("••••••"), f"API key should remain masked, got: {updated['OPENAI_API_KEY']}"
            print(f"   ✓ Updated config {config_id}")
            return updated
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_update_with_key(self, config_id):
        """Test PUT /api/configs/{id} with new API key"""
        print(f"\n5. Testing UPDATE config {config_id} with new API key...")
        update_data = {
            "name": "Config with New Key",
            "OPENAI_API_KEY": "sk-newkey1234567890"
        }
        
        try:
            response = await self.client.put(f"{API_BASE}/{config_id}", json=update_data)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            updated = response.json()
            assert updated["name"] == update_data["name"]
            # New key should be masked in response
            assert updated["OPENAI_API_KEY"].startswith("••••••"), f"API key should be masked, got: {updated['OPENAI_API_KEY']}"
            # Check it ends with last 4 chars of new key
            assert updated["OPENAI_API_KEY"].endswith("7890"), f"Should show last 4 chars of new key, got: {updated['OPENAI_API_KEY']}"
            print(f"   ✓ Updated config {config_id} with new key (masked: {updated['OPENAI_API_KEY'][:10]}...)")
            return updated
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_update_with_masked_key(self, config_id):
        """Test PUT /api/configs/{id} with masked key (should keep original)"""
        print(f"\n6. Testing UPDATE config {config_id} with masked key (keep original)...")
        # First get current config to know its masked key
        current = await self.test_get_config(config_id)
        masked_key = current["OPENAI_API_KEY"]
        
        update_data = {
            "name": "Config Keeping Original Key",
            "OPENAI_API_KEY": masked_key  # Send masked key
        }
        
        try:
            response = await self.client.put(f"{API_BASE}/{config_id}", json=update_data)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            updated = response.json()
            assert updated["name"] == update_data["name"]
            # Key should remain the same masked value
            assert updated["OPENAI_API_KEY"] == masked_key
            print(f"   ✓ Updated config {config_id} while keeping original key (masked)")
            return updated
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_delete_config(self, config_id):
        """Test DELETE /api/configs/{id}"""
        print(f"\n7. Testing DELETE config {config_id}...")
        try:
            # First verify it exists
            get_response = await self.client.get(f"{API_BASE}/{config_id}")
            assert get_response.status_code == 200
            
            # Then delete it
            delete_response = await self.client.delete(f"{API_BASE}/{config_id}")
            assert delete_response.status_code == 204, f"Expected 204, got {delete_response.status_code}"
            
            # Verify it's gone
            get_after_response = await self.client.get(f"{API_BASE}/{config_id}")
            assert get_after_response.status_code == 404, f"Expected 404 after deletion, got {get_after_response.status_code}"
            
            print(f"   ✓ Deleted config {config_id}")
            if config_id in self.created_ids:
                self.created_ids.remove(config_id)
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            raise
    
    async def test_error_cases(self):
        """Test error cases"""
        print("\n8. Testing error cases...")
        
        # Test GET non-existent config
        try:
            response = await self.client.get(f"{API_BASE}/999999")
            assert response.status_code == 404, f"Expected 404 for non-existent config, got {response.status_code}"
            print("   ✓ GET non-existent config returns 404")
        except Exception as e:
            print(f"   ✗ GET error test failed: {e}")
            raise
        
        # Test DELETE non-existent config
        try:
            response = await self.client.delete(f"{API_BASE}/999999")
            assert response.status_code == 404, f"Expected 404 for non-existent config, got {response.status_code}"
            print("   ✓ DELETE non-existent config returns 404")
        except Exception as e:
            print(f"   ✗ DELETE error test failed: {e}")
            raise
        
        # Test invalid data (missing required field)
        try:
            invalid_data = {
                "name": "Only name, missing other fields"
            }
            response = await self.client.post(API_BASE, json=invalid_data)
            # FastAPI validation should return 422 for missing fields
            assert response.status_code == 422, f"Expected 422 for invalid data, got {response.status_code}"
            print("   ✓ Invalid data returns validation error")
        except Exception as e:
            print(f"   ✗ Validation test failed: {e}")
            raise
    
    async def run_all_tests(self):
        """Run all tests"""
        try:
            await self.setup()
            
            # Test 1: List configs
            initial_configs = await self.test_list_configs()
            
            # Test 2: Create config
            created = await self.test_create_config()
            created_id = created["id"]
            
            # Test 3: Get created config
            await self.test_get_config(created_id)
            
            # Test 4: Update config (without key)
            await self.test_update_config(created_id)
            
            # Test 5: Update with new key
            await self.test_update_with_key(created_id)
            
            # Test 6: Update with masked key (keep original)
            await self.test_update_with_masked_key(created_id)
            
            # Test 7: Verify updates
            updated = await self.test_get_config(created_id)
            assert updated["name"] == "Config Keeping Original Key"
            
            # Test 8: Error cases
            await self.test_error_cases()
            
            # Test 9: Delete config (clean up)
            await self.test_delete_config(created_id)
            
            # Final list to verify deletion
            final_configs = await self.test_list_configs()
            
            print(f"\n=== All Tests Passed! ===")
            print(f"Initial configs: {len(initial_configs)}")
            print(f"Final configs: {len(final_configs)}")
            
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
    tester = APIConfigCRUDTest()
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