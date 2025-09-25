"""
Unit tests for API Client
"""
import pytest
import httpx
from unittest.mock import patch, Mock

from src.infrastructure.api.client import APIClient
from src.core.errors.exceptions import APIError, AuthenticationError


@pytest.mark.unit
class TestAPIClient:
    """Unit tests for API client functionality"""

    def test_client_initialization(self, mock_config):
        """Test API client initialization"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            client = APIClient()
            assert client.base_url == mock_config['api']['base_url']
            assert client.api_key == mock_config['api']['api_key']

    def test_client_initialization_missing_config(self):
        """Test API client initialization with missing config"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = None

            with pytest.raises(APIError, match="No configuration found"):
                APIClient()

    def test_client_headers_setup(self, mock_config):
        """Test API client headers setup"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            client = APIClient()
            headers = client._get_headers()

            assert 'Authorization' in headers
            assert headers['Authorization'] == f"Bearer {mock_config['api']['api_key']}"
            assert headers['Content-Type'] == 'application/json'

    @patch('httpx.Client.get')
    def test_successful_get_request(self, mock_get, mock_config, mock_api_response):
        """Test successful GET request"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            # Setup mock response
            mock_response = mock_api_response({'status': 'success', 'data': [{'id': 1}]})
            mock_get.return_value = mock_response

            client = APIClient()
            result = client.get('test-endpoint')

            assert result['status'] == 'success'
            assert len(result['data']) == 1
            mock_get.assert_called_once()

    @patch('httpx.Client.post')
    def test_successful_post_request(self, mock_post, mock_config, mock_api_response):
        """Test successful POST request"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            # Setup mock response
            mock_response = mock_api_response({'status': 'success', 'id': 123})
            mock_post.return_value = mock_response

            client = APIClient()
            data = {'name': 'Test Item'}
            result = client.post('test-endpoint', data)

            assert result['status'] == 'success'
            assert result['id'] == 123
            mock_post.assert_called_once()

    @patch('httpx.Client.put')
    def test_successful_put_request(self, mock_put, mock_config, mock_api_response):
        """Test successful PUT request"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_response = mock_api_response({'status': 'success'})
            mock_put.return_value = mock_response

            client = APIClient()
            data = {'name': 'Updated Item'}
            result = client.put('test-endpoint/123', data)

            assert result['status'] == 'success'
            mock_put.assert_called_once()

    @patch('httpx.Client.delete')
    def test_successful_delete_request(self, mock_delete, mock_config, mock_api_response):
        """Test successful DELETE request"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_response = mock_api_response({'status': 'success'})
            mock_delete.return_value = mock_response

            client = APIClient()
            result = client.delete('test-endpoint/123')

            assert result['status'] == 'success'
            mock_delete.assert_called_once()

    @patch('httpx.Client.get')
    def test_404_error_handling(self, mock_get, mock_config, mock_api_response):
        """Test 404 error handling"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_response = mock_api_response({'error': 'Not found'}, 404)
            mock_get.return_value = mock_response

            client = APIClient()

            with pytest.raises(APIError, match="Not found"):
                client.get('nonexistent-endpoint')

    @patch('httpx.Client.get')
    def test_401_authentication_error(self, mock_get, mock_config, mock_api_response):
        """Test 401 authentication error handling"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_response = mock_api_response({'error': 'Unauthorized'}, 401)
            mock_get.return_value = mock_response

            client = APIClient()

            with pytest.raises(AuthenticationError, match="Unauthorized"):
                client.get('protected-endpoint')

    @patch('httpx.Client.get')
    def test_500_server_error(self, mock_get, mock_config, mock_api_response):
        """Test 500 server error handling"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_response = mock_api_response({'error': 'Internal server error'}, 500)
            mock_get.return_value = mock_response

            client = APIClient()

            with pytest.raises(APIError, match="Internal server error"):
                client.get('error-endpoint')

    @patch('httpx.Client.get')
    def test_network_timeout(self, mock_get, mock_config):
        """Test network timeout handling"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_get.side_effect = httpx.TimeoutException("Request timeout")

            client = APIClient()

            with pytest.raises(APIError, match="Request timeout"):
                client.get('slow-endpoint')

    @patch('httpx.Client.get')
    def test_connection_error(self, mock_get, mock_config):
        """Test connection error handling"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            mock_get.side_effect = httpx.ConnectError("Connection failed")

            client = APIClient()

            with pytest.raises(APIError, match="Connection failed"):
                client.get('unreachable-endpoint')

    def test_request_retry_mechanism(self, mock_config, mock_api_response):
        """Test request retry mechanism"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            with patch('httpx.Client.get') as mock_get:
                # First call fails, second succeeds
                mock_get.side_effect = [
                    httpx.TimeoutException("Timeout"),
                    mock_api_response({'status': 'success'})
                ]

                client = APIClient(max_retries=2)
                result = client.get('retry-endpoint')

                assert result['status'] == 'success'
                assert mock_get.call_count == 2

    def test_request_retry_exhausted(self, mock_config):
        """Test request retry exhaustion"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            with patch('httpx.Client.get') as mock_get:
                # All calls fail
                mock_get.side_effect = httpx.TimeoutException("Always timeout")

                client = APIClient(max_retries=2)

                with pytest.raises(APIError, match="Always timeout"):
                    client.get('always-fail-endpoint')

                assert mock_get.call_count == 3  # Original + 2 retries

    def test_rate_limiting(self, mock_config):
        """Test rate limiting functionality"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            with patch('time.sleep') as mock_sleep, \
                 patch('httpx.Client.get') as mock_get:

                mock_get.return_value = Mock(status_code=200, json=lambda: {'status': 'success'})

                client = APIClient(rate_limit_delay=0.5)

                # Make multiple requests
                client.get('endpoint1')
                client.get('endpoint2')

                # Should have slept between requests
                assert mock_sleep.called

    def test_json_parsing_error(self, mock_config):
        """Test JSON parsing error handling"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            with patch('httpx.Client.get') as mock_get:
                # Mock response that can't be parsed as JSON
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json.side_effect = ValueError("Invalid JSON")
                mock_response.text = "Invalid response"

                mock_get.return_value = mock_response

                client = APIClient()

                with pytest.raises(APIError, match="Invalid JSON response"):
                    client.get('invalid-json-endpoint')

    def test_client_context_manager(self, mock_config):
        """Test API client as context manager"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            with patch('httpx.Client') as mock_httpx_client:
                mock_client_instance = Mock()
                mock_httpx_client.return_value = mock_client_instance

                with APIClient() as client:
                    assert client is not None

                # Should have called close on the underlying client
                mock_client_instance.close.assert_called_once()

    def test_custom_headers_addition(self, mock_config):
        """Test adding custom headers to requests"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            with patch('httpx.Client.get') as mock_get:
                mock_get.return_value = Mock(status_code=200, json=lambda: {'status': 'success'})

                client = APIClient()
                custom_headers = {'X-Custom-Header': 'Custom Value'}

                client.get('endpoint', headers=custom_headers)

                # Verify headers were included
                call_args = mock_get.call_args
                headers = call_args[1]['headers']
                assert 'X-Custom-Header' in headers
                assert headers['X-Custom-Header'] == 'Custom Value'

    def test_query_parameters(self, mock_config):
        """Test query parameter handling"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            with patch('httpx.Client.get') as mock_get:
                mock_get.return_value = Mock(status_code=200, json=lambda: {'status': 'success'})

                client = APIClient()
                params = {'page': 1, 'limit': 10}

                client.get('endpoint', params=params)

                # Verify params were included
                call_args = mock_get.call_args
                assert 'params' in call_args[1]
                assert call_args[1]['params'] == params

    def test_request_logging(self, mock_config, mock_logger):
        """Test request logging functionality"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config, \
             patch('src.infrastructure.api.client.get_logger') as mock_get_logger:

            mock_load_config.return_value = mock_config
            mock_get_logger.return_value = mock_logger

            with patch('httpx.Client.get') as mock_get:
                mock_get.return_value = Mock(status_code=200, json=lambda: {'status': 'success'})

                client = APIClient(enable_logging=True)
                client.get('test-endpoint')

                # Should have logged the request
                mock_logger.info.assert_called()

    def test_response_caching(self, mock_config, mock_api_response):
        """Test response caching functionality"""
        with patch('src.infrastructure.api.client.load_config') as mock_load_config:
            mock_load_config.return_value = mock_config

            with patch('httpx.Client.get') as mock_get:
                mock_response = mock_api_response({'status': 'success', 'data': 'cached'})
                mock_get.return_value = mock_response

                client = APIClient(enable_cache=True, cache_ttl=60)

                # First request
                result1 = client.get('cacheable-endpoint')

                # Second request should use cache
                result2 = client.get('cacheable-endpoint')

                assert result1 == result2
                # Should only call the API once due to caching
                assert mock_get.call_count == 1