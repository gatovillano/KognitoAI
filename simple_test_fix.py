#!/usr/bin/env python3
"""
Simple test to verify ConceptualProcessingTool can be imported without errors.
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/home/gato/KognitoAI/kognito-ai')

def test_simple_import():
    """Test that ConceptualProcessingTool can be imported without errors."""
    try:
        print("🚀 Testing simple import of ConceptualProcessingTool...")
        
        # This should work without triggering the pickling error
        from tools.conceptual_processing_tool import ConceptualProcessingTool
        
        print("✅ Successfully imported ConceptualProcessingTool")
        
        # Try basic instantiation
        tool = ConceptualProcessingTool(account_id="test-123")
        print("✅ Successfully instantiated ConceptualProcessingTool")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simple_import()
    if success:
        print("\n🎉 Test passed! The pickling issue appears to be resolved.")
        sys.exit(0)
    else:
        print("\n💥 Test failed.")
        sys.exit(1)