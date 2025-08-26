#!/usr/bin/env python3
"""
Simple test suite for get_dashboard_list method refactoring
"""

import pytest
import asyncio
import requests
from unittest.mock import Mock, patch, AsyncMock

# Import the SupersetAutomation class
from superset_automation import SupersetAutomation


class TestDashboardListSimple:
    """Simple test suite for dashboard list API functionality"""
    
    @pytest.fixture
    def automation_instance(self):
        """Create a SupersetAutomation instance for testing"""
        with patch('superset_automation.PLAYWRIGHT_AVAILABLE', True):
            automation = SupersetAutomation()
            # Mock browser-related attributes to avoid actual browser initialization
            automation.playwright = None
            automation.browser = None
            automation.page = None
            automation.session_cookies = None
            return automation
    
    @pytest.mark.asyncio
    async def test_get_dashboard_list_api_success(self, automation_instance):
        """Test successful dashboard list retrieval via API"""
        with patch('requests.get') as mock_get:
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'result': [
                    {
                        'id': 1,
                        'dashboard_title': 'Test Dashboard 1',
                        'published': True
                    },
                    {
                        'id': 2,
                        'dashboard_title': 'Test Dashboard 2',
                        'published': False
                    }
                ]
            }
            mock_get.return_value = mock_response
            
            # Call the method
            result = await automation_instance.get_dashboard_list()
            
            # Verify the request was made correctly
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert args[0] == f"{automation_instance.superset_url}/api/v1/dashboard/"
            assert kwargs['headers']['Content-Type'] == 'application/json'
            assert kwargs['headers']['Accept'] == 'application/json'
            assert kwargs['timeout'] == 30
            
            # Verify the result
            assert len(result) == 2
            assert result[0]['id'] == 1
            assert result[0]['title'] == 'Test Dashboard 1'
            assert result[0]['url'] == '/dashboard/1/'
            assert result[0]['published'] is True
    
    @pytest.mark.asyncio
    async def test_get_dashboard_list_api_401_auto_login(self, automation_instance):
        """Test 401 response triggers automatic login and retry"""
        with patch('requests.get') as mock_get, \
             patch.object(automation_instance, 'login_to_superset', new_callable=AsyncMock) as mock_login:
            
            # Mock 401 response first, then successful response
            mock_401_response = Mock()
            mock_401_response.status_code = 401
            
            mock_success_response = Mock()
            mock_success_response.status_code = 200
            mock_success_response.json.return_value = {
                'result': [
                    {
                        'id': 1,
                        'dashboard_title': 'Test Dashboard 1',
                        'published': True
                    }
                ]
            }
            
            mock_get.side_effect = [mock_401_response, mock_success_response]
            mock_login.return_value = True
            
            # Call the method
            result = await automation_instance.get_dashboard_list()
            
            # Verify login was attempted
            mock_login.assert_called_once()
            
            # Verify two requests were made
            assert mock_get.call_count == 2
            
            # Verify the result
            assert len(result) == 1
            assert result[0]['id'] == 1
    
    @pytest.mark.asyncio
    async def test_get_dashboard_list_api_request_exception_triggers_fallback(self, automation_instance):
        """Test request exception triggers fallback"""
        with patch('requests.get') as mock_get, \
             patch.object(automation_instance, '_get_dashboard_list_fallback', new_callable=AsyncMock) as mock_fallback:
            
            # Mock request exception
            mock_get.side_effect = requests.exceptions.RequestException("Connection error")
            mock_fallback.return_value = [{'id': 999, 'title': 'Fallback Dashboard', 'url': '/dashboard/999/'}]
            
            # Call the method
            result = await automation_instance.get_dashboard_list()
            
            # Verify fallback was called
            mock_fallback.assert_called_once()
            
            # Verify fallback result
            assert len(result) == 1
            assert result[0]['id'] == 999
            assert result[0]['title'] == 'Fallback Dashboard'
    
    @pytest.mark.asyncio
    async def test_get_dashboard_list_fallback_method(self, automation_instance):
        """Test fallback method functionality"""
        # Set page to None to trigger browser initialization
        automation_instance.page = None
        
        # Mock page and its methods
        mock_page = AsyncMock()
        mock_dashboards = [
            {
                'id': 1,
                'title': 'Fallback Dashboard 1',
                'url': '/dashboard/1/',
                'element_count': 5
            }
        ]
        mock_page.evaluate.return_value = mock_dashboards
        
        # Mock browser initialization
        with patch.object(automation_instance, 'initialize_browser', new_callable=AsyncMock) as mock_init:
            mock_init.return_value = True
            # Directly set the page after initialization
            def side_effect(*args, **kwargs):
                automation_instance.page = mock_page
                return True
            mock_init.side_effect = side_effect
                
            # Call the fallback method
            result = await automation_instance._get_dashboard_list_fallback()
            
            # Verify browser initialization
            mock_init.assert_called_once()
            
            # Verify page navigation
            mock_page.goto.assert_called_once_with(f"{automation_instance.superset_url}/dashboard/list/")
            
            # Verify JavaScript evaluation
            mock_page.evaluate.assert_called_once()
            
            # Verify result
            assert len(result) == 1
            assert result[0]['id'] == 1
            assert result[0]['title'] == 'Fallback Dashboard 1'


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
