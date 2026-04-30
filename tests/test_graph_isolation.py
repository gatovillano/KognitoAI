
import asyncio
import logging
import uuid
from knowledge_graph.graph_database import GraphDB
from knowledge_graph.graph_integration import GraphIntegration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_workspace_isolation():
    graph_db = GraphDB()
    graph_integration = GraphIntegration()
    
    account_id = f"test_acc_{uuid.uuid4().hex[:8]}"
    ws_a = str(uuid.uuid4())
    ws_b = str(uuid.uuid4())
    
    dataset_name = "IsolationTest"
    
    logger.info(f"🚀 Starting Isolation Test for Account: {account_id}")
    logger.info(f"Workspace A: {ws_a}")
    logger.info(f"Workspace B: {ws_b}")

    try:
        # 1. Clean up if exists (shouldn't)
        await graph_db.delete_dataset(dataset_name, account_id, ws_a)
        await graph_db.delete_dataset(dataset_name, account_id, ws_b)
        await graph_db.delete_dataset(dataset_name, account_id, None)

        # 2. Create nodes in different workspaces
        # Node in WS_A
        await graph_db.execute_query(
            "CREATE (n:Entity {id: $id, name: $name, dataset_name: $dataset, account_id: $acc, workspace_id: $ws})",
            {"id": "node_a", "name": "Secret A", "dataset": dataset_name, "acc": account_id, "ws": ws_a}
        )
        
        # Node in WS_B
        await graph_db.execute_query(
            "CREATE (n:Entity {id: $id, name: $name, dataset_name: $dataset, account_id: $acc, workspace_id: $ws})",
            {"id": "node_b", "name": "Secret B", "dataset": dataset_name, "acc": account_id, "ws": ws_b}
        )
        
        # Global Node (NULL workspace)
        await graph_db.execute_query(
            "CREATE (n:Entity {id: $id, name: $name, dataset_name: $dataset, account_id: $acc})",
            {"id": "node_global", "name": "Global Info", "dataset": dataset_name, "acc": account_id}
        )

        logger.info("✅ Test nodes created.")

        # 3. Test get_available_datasets for WS_A
        logger.info("--- Testing get_available_datasets for WS_A ---")
        datasets_a = await graph_db.get_available_datasets(account_id, ws_a)
        logger.info(f"Datasets in WS_A: {datasets_a}")
        assert any(d['name'] == dataset_name for d in datasets_a), "Dataset should be visible in WS_A"
        
        # Verify node count in dataset for WS_A
        # Note: get_available_datasets returns count per dataset_name
        count_a = next(d['node_count'] for d in datasets_a if d['name'] == dataset_name)
        logger.info(f"Node count in WS_A: {count_a}")
        assert count_a == 1, f"Expected 1 node in WS_A, got {count_a}"

        # 4. Test search_knowledge_graph for WS_A
        logger.info("--- Testing search_knowledge_graph for WS_A ---")
        # Direct query
        query_a = """
        MATCH (n) 
        WHERE n.dataset_name = $dataset_name 
          AND n.account_id = $account_id 
          AND n.workspace_id = $workspace_id
        RETURN n.name as name
        """
        results_a = await graph_db.execute_query(query_a, {"dataset_name": dataset_name, "account_id": account_id, "workspace_id": ws_a})
        names_a = [r['name'] for r in results_a]
        logger.info(f"Nodes found in WS_A: {names_a}")
        assert "Secret A" in names_a, "Secret A should be in WS_A"
        assert "Secret B" not in names_a, "Secret B should NOT be in WS_A"
        assert "Global Info" not in names_a, "Global Info should NOT be in WS_A (Strict Isolation)"

        # 5. Test search_knowledge_graph for NULL workspace (Global)
        logger.info("--- Testing search_knowledge_graph for Global (NULL) ---")
        query_global = """
        MATCH (n) 
        WHERE n.dataset_name = $dataset_name 
          AND n.account_id = $account_id 
          AND n.workspace_id IS NULL
        RETURN n.name as name
        """
        results_global = await graph_db.execute_query(query_global, {"dataset_name": dataset_name, "account_id": account_id})
        names_global = [r['name'] for r in results_global]
        logger.info(f"Nodes found in Global: {names_global}")
        assert "Global Info" in names_global, "Global Info should be in Global context"
        assert "Secret A" not in names_global, "Secret A should NOT be in Global context"
        assert "Secret B" not in names_global, "Secret B should NOT be in Global context"

        logger.info("⭐⭐⭐ ALL ISOLATION TESTS PASSED ⭐⭐⭐")

    finally:
        # Clean up
        logger.info("🧹 Cleaning up test data...")
        await graph_db.execute_query(
            "MATCH (n) WHERE n.account_id = $acc AND n.dataset_name = $dataset DELETE n",
            {"acc": account_id, "dataset": dataset_name}
        )

if __name__ == "__main__":
    asyncio.run(test_workspace_isolation())
