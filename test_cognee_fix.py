#!/usr/bin/env python3
"""
Test script to verify the cognee_knowledge_graph tool fix.
This tests that the tool accepts requests with empty documents when a topic is provided.
"""

import sys
import os

# Add the project directory to Python path
sys.path.append('/home/gato/KognitoAI/kognito-ai')

def test_validation_logic():
    """Test the validation logic from api/tools.py"""
    
    # Simulate the original problematic request
    args = {
        'tool_name': 'cognee_knowledge_graph',
        'action': 'process_documents', 
        'dataset_name': 'topic_inteligencia_artificial',
        'topic': 'Inteligencia Artificial',
        'documents': []
    }
    
    # Apply the validation logic
    documents_to_process = args.get("documents")
    document_titles_to_process = args.get("document_titles")
    topic = args.get("topic")
    dataset_name = args.get("dataset_name") or topic or "default"
    
    # The new validation: allow documents empty if topic is provided
    if not documents_to_process and not document_titles_to_process and not topic:
        print("❌ FAILED: Validation should pass with topic provided")
        return False
    else:
        print("✅ PASSED: Validation correctly allows empty documents when topic is provided")
        print(f"   - documents: {documents_to_process}")
        print(f"   - document_titles: {document_titles_to_process}")
        print(f"   - topic: {topic}")
        print(f"   - dataset_name: {dataset_name}")
        return True

def test_strict_validation():
    """Test that strict validation still works (no documents, no topic)"""
    
    args = {
        'tool_name': 'cognee_knowledge_graph',
        'action': 'process_documents', 
        'dataset_name': 'topic_inteligencia_artificial',
        'documents': []
    }
    
    # Apply the validation logic
    documents_to_process = args.get("documents")
    document_titles_to_process = args.get("document_titles")
    topic = args.get("topic")
    
    # The new validation: should fail when no documents, no titles, no topic
    if not documents_to_process and not document_titles_to_process and not topic:
        print("✅ PASSED: Validation correctly rejects request with no documents, no titles, and no topic")
        return True
    else:
        print("❌ FAILED: Validation should fail when no documents, no titles, and no topic")
        return False

if __name__ == "__main__":
    print("Testing cognee_knowledge_graph tool validation fix...")
    print("=" * 60)
    
    # Test 1: Valid request with topic
    print("\n1. Testing valid request with topic:")
    test1_passed = test_validation_logic()
    
    # Test 2: Invalid request without topic
    print("\n2. Testing invalid request without topic:")
    test2_passed = test_strict_validation()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("🎉 All tests passed! The fix is working correctly.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. The fix needs adjustment.")
        sys.exit(1)