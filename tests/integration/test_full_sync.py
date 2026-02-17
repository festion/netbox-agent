import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from src.netbox_agent import NetBoxAgent

@pytest.mark.integration
class TestFullSyncWorkflow:
    """Test complete sync workflow from discovery to NetBox"""
    
    @pytest.fixture
    async def agent(self, test_config, tmp_path):
        """Create NetBox agent for testing"""
        
        # Create temporary config file
        config_file = tmp_path / "test-config.json"
        
        with patch('src.netbox_agent.NetBoxAgent._load_config') as mock_load:
            mock_load.return_value = Mock(**test_config)
            
            with patch('src.netbox_agent.NetBoxClient'):
                agent = NetBoxAgent(str(config_file))
                
                # Mock all external dependencies
                agent.netbox_client.test_connection = AsyncMock(return_value=True)
                agent.data_source_manager.discover_all_devices = AsyncMock(return_value={
                    "homeassistant": [Mock(name="ha-device-1", dict=lambda: {"name": "ha-device-1"})],
                    "network_scan": [Mock(name="scan-device-1", dict=lambda: {"name": "scan-device-1"})]
                })
                
                return agent
    
    @pytest.mark.asyncio
    async def test_full_sync_workflow(self, agent):
        """Test complete full sync workflow"""
        
        # Mock sync engine
        agent.sync_engine.build_caches = AsyncMock()
        agent.sync_engine.sync_devices_batch = AsyncMock(return_value=[
            Mock(action=Mock(value="create"), success=True, conflicts=None),
            Mock(action=Mock(value="update"), success=True, conflicts=None)
        ])
        
        # Execute full sync
        await agent.perform_full_sync()
        
        # Verify workflow execution
        agent.sync_engine.build_caches.assert_called_once()
        agent.data_source_manager.discover_all_devices.assert_called_once()
        
        # Verify sync was called for each source
        assert agent.sync_engine.sync_devices_batch.call_count == 2
    
    @pytest.mark.asyncio
    async def test_error_handling_during_sync(self, agent):
        """Test error handling during sync operations"""
        
        # Mock an error in one data source
        agent.data_source_manager.discover_all_devices = AsyncMock(side_effect=Exception("Test error"))
        
        # Should not raise exception
        await agent.perform_full_sync()
        
        # Verify error was logged (would need to capture logs in real test)
        # This is a simplified test - full implementation would verify logging