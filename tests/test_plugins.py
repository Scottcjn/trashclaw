import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the plugins directory to the path to import plugins
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'plugins'))

class TestPlugins(unittest.TestCase):
    """Test suite for all plugins in TrashClaw"""
    
    def setUp(self):
        """Set up test environment"""
        # Mock the LLM server connection
        self.mock_llm = MagicMock()
        self.mock_llm.send_message.return_value = "Mock response"
        
    def test_plugin_loading(self):
        """Test that all plugins can be loaded without errors"""
        plugins_dir = os.path.join(os.path.dirname(__file__), '..', 'plugins')
        plugin_files = [f for f in os.listdir(plugins_dir) if f.endswith('.py') and f != '__init__.py']
        
        for plugin_file in plugin_files:
            try:
                plugin_name = plugin_file[:-3]  # Remove .py extension
                module = __import__(f'plugins.{plugin_name}', fromlist=[plugin_name])
                self.assertTrue(hasattr(module, 'Plugin'), f"Plugin {plugin_name} must have a Plugin class")
                self.assertTrue(hasattr(module.Plugin, 'execute'), f"Plugin {plugin_name} must have an execute method")
            except Exception as e:
                self.fail(f"Failed to load plugin {plugin_name}: {str(e)}")
    
    def test_plugin_execution(self):
        """Test that all plugins can execute without errors"""
        plugins_dir = os.path.join(os.path.dirname(__file__), '..', 'plugins')
        plugin_files = [f for f in os.listdir(plugins_dir) if f.endswith('.py') and f != '__init__.py']
        
        for plugin_file in plugin_files:
            try:
                plugin_name = plugin_file[:-3]  # Remove .py extension
                module = __import__(f'plugins.{plugin_name}', fromlist=[plugin_name])
                plugin = module.Plugin()
                
                # Mock the plugin's dependencies
                with patch.object(plugin, '_get_llm_response', return_value="Mock response"):
                    with patch.object(plugin, '_execute_command', return_value="Command executed"):
                        result = plugin.execute("test input")
                        self.assertIsNotNone(result, f"Plugin {plugin_name} execute returned None")
            except Exception as e:
                self.fail(f"Failed to execute plugin {plugin_name}: {str(e)}")
    
    def test_plugin_parameters(self):
        """Test that all plugins handle parameters correctly"""
        plugins_dir = os.path.join(os.path.dirname(__file__), '..', 'plugins')
        plugin_files = [f for f in os.listdir(plugins_dir) if f.endswith('.py') and f != '__init__.py']
        
        for plugin_file in plugin_files:
            try:
                plugin_name = plugin_file[:-3]  # Remove .py extension
                module = __import__(f'plugins.{plugin_name}', fromlist=[plugin_name])
                plugin = module.Plugin()
                
                # Test with empty parameters
                with patch.object(plugin, '_get_llm_response', return_value="Mock response"):
                    with patch.object(plugin, '_execute_command', return_value="Command executed"):
                        result = plugin.execute("")
                        self.assertIsNotNone(result, f"Plugin {plugin_name} should handle empty parameters")
            except Exception as e:
                self.fail(f"Plugin {plugin_name} failed with empty parameters: {str(e)}")

if __name__ == '__main__':
    unittest.main()