#!/usr/bin/env python3
"""
Test script to verify that ConceptualProcessingTool can be instantiated without pickling errors.
"""

import sys
import os
import pickle
import traceback

# Add the project root to Python path
sys.path.insert(0, '/home/gato/KognitoAI/kognito-ai')

def test_conceptual_tool_instantiation():
    """Test that ConceptualProcessingTool can be instantiated and pickled."""
    try:
        # Import the tool
        from tools.conceptual_processing_tool import ConceptualProcessingTool
        
        print("✅ Successfully imported ConceptualProcessingTool")
        
        # Try to instantiate without dependencies
        tool = ConceptualProcessingTool(
            account_id="test-account-123",
            workspace_id="test-workspace-456"
        )
        
        print("✅ Successfully instantiated ConceptualProcessingTool")
        
        # Try to pickle the tool
        try:
            pickled_data = pickle.dumps(tool)
            print("✅ Successfully pickled ConceptualProcessingTool")
            
            # Try to unpickle
            unpickled_tool = pickle.loads(pickled_data)
            print("✅ Successfully unpickled ConceptualProcessingTool")
            
            # Verify basic attributes
            assert unpickled_tool.account_id == "test-account-123"
            assert unpickled_tool.workspace_id == "test-workspace-456"
            print("✅ Basic attributes preserved after pickling/unpickling")
            
            return True
            
        except Exception as pickle_error:
            print(f"❌ Pickling failed: {pickle_error}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Failed to import or instantiate ConceptualProcessingTool: {e}")
        traceback.print_exc()
        return False

def test_with_dependencies():
    """Test with injected dependencies."""
    try:
        from tools.conceptual_processing_tool import ConceptualProcessingTool
        
        print("\n🧪 Testing with mock dependencies...")
        
        # Create a mock dependency
        class MockGraphIntegration:
            def __init__(self):
                self.test_attr = "mock_integration"
        
        # Try to instantiate with dependencies
        tool = ConceptualProcessingTool(
            account_id="test-account-123",
            graph_integration=MockGraphIntegration()
        )
        
        print("✅ Successfully instantiated with dependencies")
        
        # Try to pickle
        try:
            pickled_data = pickle.dumps(tool)
            print("✅ Successfully pickled with dependencies")
            
            unpickled_tool = pickle.loads(pickled_data)
            print("✅ Successfully unpickled with dependencies")
            
            return True
            
        except Exception as pickle_error:
            print(f"❌ Pickling with dependencies failed: {pickle_error}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Failed with dependencies: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing ConceptualProcessingTool pickling fix...")
    print("=" * 60)
    
    # Test basic instantiation
    basic_test_passed = test_conceptual_tool_instantiation()
    
    # Test with dependencies
    deps_test_passed = test_with_dependencies()
    
    print("\n" + "=" * 60)
    print("📊 Test Results:")
    print(f"  Basic instantiation: {'✅ PASS' if basic_test_passed else '❌ FAIL'}")
    print(f"  With dependencies:   {'✅ PASS' if deps_test_passed else '❌ FAIL'}")
    
    if basic_test_passed and deps_test_passed:
        print("\n🎉 All tests passed! The pickling issue has been resolved.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed. The issue may not be fully resolved.")
        sys.exit(1)