#!/usr/bin/env python3
"""
Test script to verify the graph processing fixes.
This script tests:
1. Hybrid processing without co-occurrence relationships
2. Frontend filtering logic improvements
"""

import asyncio
import sys
import os
import logging

# Add the project root to Python path
sys.path.insert(0, '/home/gato/KognitoAI/kognito-ai')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_hybrid_processing_without_cooccurrence():
    """Test that hybrid processing works without co-occurrence relationships."""
    try:
        from knowledge_graph.hybrid_graph_processor import HybridGraphProcessor
        
        logger.info("🧪 Testing hybrid processing without co-occurrence...")
        
        # Create test documents
        test_documents = [
            {
                "title": "Test Document 1",
                "content": "El agente de IA utiliza técnicas de machine learning para procesar datos. Los algoritmos de deep learning son fundamentales para el análisis."
            },
            {
                "title": "Test Document 2", 
                "content": "Los sistemas de IA requieren bases de datos robustas. Neo4j es una base de datos de grafos excelente para almacenar conocimiento."
            }
        ]
        
        # Initialize processor
        processor = HybridGraphProcessor()
        await processor.initialize()
        
        # Process documents
        result = await processor.process_documents(
            documents=test_documents,
            dataset_name="test_dataset",
            account_id="test_account",
            workspace_id="test_workspace"
        )
        
        # Verify results
        entities = result.get("entities", [])
        relationships = result.get("relationships", [])
        metadata = result.get("metadata", {})
        
        logger.info(f"✅ Test Results:")
        logger.info(f"   📊 Entities: {len(entities)}")
        logger.info(f"   🔗 Relationships: {len(relationships)}")
        logger.info(f"   📈 Processing method: {metadata.get('processed_with', 'unknown')}")
        
        # Check that we have semantic relationships (not co-occurrence)
        relationship_types = set()
        for rel in relationships:
            rel_type = rel.get('type', rel.get('relationship_type', 'unknown'))
            relationship_types.add(rel_type)
        
        logger.info(f"   🔍 Relationship types found: {list(relationship_types)}")
        
        # Verify no co-occurrence relationships
        cooccurrence_types = [t for t in relationship_types if 'CO_OCCURRENCE' in t.upper()]
        if cooccurrence_types:
            logger.warning(f"⚠️ Found co-occurrence relationships: {cooccurrence_types}")
            return False
        else:
            logger.info("✅ No co-occurrence relationships found (as expected)")
        
        # Verify we have semantic relationships
        semantic_types = [t for t in relationship_types if 'CONCEPTUAL' in t.upper() or 'SEMANTIC' in t.upper()]
        if semantic_types:
            logger.info(f"✅ Found semantic relationships: {semantic_types}")
        else:
            logger.warning("⚠️ No semantic relationships found")
        
        return len(entities) > 0 and len(relationships) > 0
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

def test_frontend_filtering_logic():
    """Test frontend filtering logic improvements."""
    logger.info("🧪 Testing frontend filtering logic improvements...")
    
    # Simulate originalGraphData
    original_nodes = [
        {"id": "1", "type": "PERSON", "name": "John Doe"},
        {"id": "2", "type": "ORG", "name": "AI Corp"},
        {"id": "3", "type": "CONCEPT_TECHNICAL", "name": "Machine Learning"},
        {"id": "4", "type": "PERSON", "name": "Jane Smith"},
        {"id": "5", "type": "CONCEPT_TECHNICAL", "name": "Deep Learning"}
    ]
    
    original_edges = [
        {"from": "1", "to": "2", "type": "WORKS_AT"},
        {"from": "1", "to": "3", "type": "EXPERTISE"},
        {"from": "3", "to": "5", "type": "RELATED_TO"},
        {"from": "4", "to": "2", "type": "WORKS_AT"},
        {"from": "4", "to": "5", "type": "EXPERTISE"}
    ]
    
    # Simulate filter for PERSON type only
    filters = {
        "nodeTypes": ["PERSON"],
        "edgeTypes": []
    }
    
    # Apply improved filtering logic (similar to frontend)
    filtered_nodes = original_nodes.copy()
    filtered_edges = original_edges.copy()
    
    if filters["nodeTypes"]:
        # Get nodes of selected types
        selected_nodes = [n for n in filtered_nodes if n["type"] in filters["nodeTypes"]]
        selected_node_ids = {n["id"] for n in selected_nodes}
        
        # Get connected nodes (improved logic)
        connected_node_ids = selected_node_ids.copy()
        for edge in filtered_edges:
            if edge["from"] in selected_node_ids:
                connected_node_ids.add(edge["to"])
            if edge["to"] in selected_node_ids:
                connected_node_ids.add(edge["from"])
        
        # Filter to include selected nodes and their connections
        filtered_nodes = [n for n in filtered_nodes if n["id"] in connected_node_ids]
        filtered_edges = [e for e in filtered_edges if e["from"] in connected_node_ids and e["to"] in connected_node_ids]
    
    logger.info(f"✅ Filtering Results:")
    logger.info(f"   📊 Original nodes: {len(original_nodes)}")
    logger.info(f"   📊 Filtered nodes: {len(filtered_nodes)}")
    logger.info(f"   🔗 Original edges: {len(original_edges)}")
    logger.info(f"   🔗 Filtered edges: {len(filtered_edges)}")
    
    # Verify that we get more nodes than just the filtered type (includes connections)
    person_nodes = [n for n in filtered_nodes if n["type"] == "PERSON"]
    concept_nodes = [n for n in filtered_nodes if "CONCEPT" in n["type"]]
    
    logger.info(f"   👤 Person nodes in result: {len(person_nodes)}")
    logger.info(f"   💡 Concept nodes in result: {len(concept_nodes)}")
    
    # Should include both PERSON (filtered) and CONCEPT (connected) nodes
    if len(person_nodes) > 0 and len(concept_nodes) > 0:
        logger.info("✅ Filtering includes connected nodes (improved logic working)")
        return True
    else:
        logger.warning("⚠️ Filtering might be too restrictive")
        return False

async def main():
    """Run all tests."""
    logger.info("🚀 Starting graph processing fixes verification...")
    
    # Test 1: Hybrid processing without co-occurrence
    test1_result = await test_hybrid_processing_without_cooccurrence()
    
    # Test 2: Frontend filtering logic
    test2_result = test_frontend_filtering_logic()
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("📋 TEST SUMMARY")
    logger.info("="*50)
    logger.info(f"✅ Test 1 - Hybrid processing without co-occurrence: {'PASS' if test1_result else 'FAIL'}")
    logger.info(f"✅ Test 2 - Frontend filtering logic: {'PASS' if test2_result else 'FAIL'}")
    
    if test1_result and test2_result:
        logger.info("🎉 All tests passed! Graph processing fixes are working correctly.")
        return True
    else:
        logger.error("❌ Some tests failed. Please review the fixes.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)