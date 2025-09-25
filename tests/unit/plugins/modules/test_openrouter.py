#!/usr/bin/env python3

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from ansible.module_utils.basic import AnsibleModule

# Import the module to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../plugins/modules'))
from openrouter import run_module, make_openrouter_request


class TestOpenRouterModule:
    """Unit tests for OpenRouter module"""

    def test_parameter_validation_temperature_too_high(self):
        """Test that temperature > 2.0 fails validation"""
        with patch('openrouter.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            mock_instance.params = {
                'api_key': 'test-key',
                'prompt': 'test prompt',
                'model': 'openai/gpt-3.5-turbo',
                'system_message': None,
                'temperature': 3.0,
                'top_p': None,
                'max_tokens': None,
                'frequency_penalty': None,
                'presence_penalty': None,
                'retry_attempts': 3,
                'retry_delay': 5,
                'raw_json_output': False,
                'timeout': 30
            }

            with patch('openrouter.HAS_REQUESTS', True):
                run_module()
                mock_instance.fail_json.assert_called_once()
                call_args = mock_instance.fail_json.call_args[1]
                assert 'temperature' in call_args['msg']

    def test_parameter_validation_temperature_too_low(self):
        """Test that temperature < 0.0 fails validation"""
        with patch('openrouter.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            mock_instance.params = {
                'api_key': 'test-key',
                'prompt': 'test prompt',
                'model': 'openai/gpt-3.5-turbo',
                'system_message': None,
                'temperature': -0.5,
                'top_p': None,
                'max_tokens': None,
                'frequency_penalty': None,
                'presence_penalty': None,
                'retry_attempts': 3,
                'retry_delay': 5,
                'raw_json_output': False,
                'timeout': 30
            }

            with patch('openrouter.HAS_REQUESTS', True):
                run_module()
                mock_instance.fail_json.assert_called_once()
                call_args = mock_instance.fail_json.call_args[1]
                assert 'temperature' in call_args['msg']

    def test_parameter_validation_max_tokens_negative(self):
        """Test that negative max_tokens fails validation"""
        with patch('openrouter.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            mock_instance.params = {
                'api_key': 'test-key',
                'prompt': 'test prompt',
                'model': 'openai/gpt-3.5-turbo',
                'system_message': None,
                'temperature': None,
                'top_p': None,
                'max_tokens': -10,
                'frequency_penalty': None,
                'presence_penalty': None,
                'retry_attempts': 3,
                'retry_delay': 5,
                'raw_json_output': False,
                'timeout': 30
            }

            with patch('openrouter.HAS_REQUESTS', True):
                run_module()
                mock_instance.fail_json.assert_called_once()
                call_args = mock_instance.fail_json.call_args[1]
                assert 'max_tokens' in call_args['msg']

    @patch('openrouter.requests.post')
    def test_successful_request(self, mock_post):
        """Test successful API request"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{
                'message': {
                    'content': 'Test response'
                }
            }],
            'usage': {
                'prompt_tokens': 10,
                'completion_tokens': 5,
                'total_tokens': 15
            },
            'model': 'openai/gpt-3.5-turbo'
        }
        mock_post.return_value = mock_response

        with patch('openrouter.module') as mock_module:
            mock_module.warn = Mock()
            mock_module.fail_json = Mock()

            result = make_openrouter_request(
                api_key='test-key',
                payload={'model': 'openai/gpt-3.5-turbo', 'messages': []},
                timeout=30,
                retry_attempts=3,
                retry_delay=5
            )

            assert result['choices'][0]['message']['content'] == 'Test response'
            assert result['usage']['total_tokens'] == 15

    @patch('openrouter.requests.post')
    def test_rate_limit_retry(self, mock_post):
        """Test rate limit retry logic"""
        # First request returns 429, second succeeds
        mock_response_429 = Mock()
        mock_response_429.status_code = 429

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            'choices': [{'message': {'content': 'Success after retry'}}],
            'usage': {'total_tokens': 10}
        }

        mock_post.side_effect = [mock_response_429, mock_response_200]

        with patch('openrouter.module') as mock_module:
            mock_module.warn = Mock()
            mock_module.fail_json = Mock()

            with patch('openrouter.time.sleep'):  # Mock sleep to speed up test
                result = make_openrouter_request(
                    api_key='test-key',
                    payload={'model': 'openai/gpt-3.5-turbo', 'messages': []},
                    timeout=30,
                    retry_attempts=3,
                    retry_delay=1
                )

                assert result['choices'][0]['message']['content'] == 'Success after retry'
                mock_module.warn.assert_called()  # Should have warned about rate limit

    @patch('openrouter.requests.post')
    def test_authentication_error(self, mock_post):
        """Test authentication error handling"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        with patch('openrouter.module') as mock_module:
            mock_module.warn = Mock()
            mock_module.fail_json = Mock()

            make_openrouter_request(
                api_key='invalid-key',
                payload={'model': 'openai/gpt-3.5-turbo', 'messages': []},
                timeout=30,
                retry_attempts=3,
                retry_delay=5
            )

            mock_module.fail_json.assert_called_once()
            call_args = mock_module.fail_json.call_args[1]
            assert 'authentication' in call_args['msg'].lower()

    @patch('openrouter.requests.post')
    def test_bad_request_error(self, mock_post):
        """Test bad request error handling"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'error': {'message': 'Invalid model specified'}
        }
        mock_post.return_value = mock_response

        with patch('openrouter.module') as mock_module:
            mock_module.warn = Mock()
            mock_module.fail_json = Mock()

            make_openrouter_request(
                api_key='test-key',
                payload={'model': 'invalid/model', 'messages': []},
                timeout=30,
                retry_attempts=3,
                retry_delay=5
            )

            mock_module.fail_json.assert_called_once()
            call_args = mock_module.fail_json.call_args[1]
            assert 'Invalid model specified' in call_args['msg']

    def test_missing_requests_library(self):
        """Test behavior when requests library is not available"""
        with patch('openrouter.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance

            with patch('openrouter.HAS_REQUESTS', False):
                run_module()
                mock_instance.fail_json.assert_called_once()
                call_args = mock_instance.fail_json.call_args[1]
                assert 'requests' in call_args['msg']

    def test_successful_run_with_system_message(self):
        """Test successful module run with system message"""
        with patch('openrouter.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            mock_instance.params = {
                'api_key': 'test-key',
                'prompt': 'test prompt',
                'model': 'openai/gpt-3.5-turbo',
                'system_message': 'You are a helpful assistant',
                'temperature': 0.7,
                'top_p': None,
                'max_tokens': 100,
                'frequency_penalty': None,
                'presence_penalty': None,
                'retry_attempts': 3,
                'retry_delay': 5,
                'raw_json_output': False,
                'timeout': 30
            }

            mock_response_data = {
                'choices': [{
                    'message': {
                        'content': 'Test response'
                    }
                }],
                'usage': {
                    'prompt_tokens': 20,
                    'completion_tokens': 10,
                    'total_tokens': 30
                },
                'model': 'openai/gpt-3.5-turbo'
            }

            with patch('openrouter.HAS_REQUESTS', True):
                with patch('openrouter.make_openrouter_request', return_value=mock_response_data):
                    run_module()

                    mock_instance.exit_json.assert_called_once()
                    call_args = mock_instance.exit_json.call_args[1]
                    assert call_args['changed'] is True
                    assert call_args['result']['text'] == 'Test response'
                    assert call_args['result']['usage']['total_tokens'] == 30

    def test_successful_run_raw_output(self):
        """Test successful module run with raw JSON output"""
        with patch('openrouter.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            mock_instance.params = {
                'api_key': 'test-key',
                'prompt': 'test prompt',
                'model': 'openai/gpt-3.5-turbo',
                'system_message': None,
                'temperature': None,
                'top_p': None,
                'max_tokens': None,
                'frequency_penalty': None,
                'presence_penalty': None,
                'retry_attempts': 3,
                'retry_delay': 5,
                'raw_json_output': True,
                'timeout': 30
            }

            mock_response_data = {
                'choices': [{'message': {'content': 'Test response'}}],
                'usage': {'total_tokens': 30},
                'model': 'openai/gpt-3.5-turbo'
            }

            with patch('openrouter.HAS_REQUESTS', True):
                with patch('openrouter.make_openrouter_request', return_value=mock_response_data):
                    run_module()

                    mock_instance.exit_json.assert_called_once()
                    call_args = mock_instance.exit_json.call_args[1]
                    assert call_args['changed'] is True
                    assert call_args['raw_response'] == mock_response_data

    @patch('openrouter.requests.post')
    def test_connection_error_retry(self, mock_post):
        """Test connection error retry logic"""
        import requests

        # First request raises ConnectionError, second succeeds
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            'choices': [{'message': {'content': 'Success after connection retry'}}],
            'usage': {'total_tokens': 10}
        }

        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            mock_response_success
        ]

        with patch('openrouter.module') as mock_module:
            mock_module.warn = Mock()
            mock_module.fail_json = Mock()

            with patch('openrouter.time.sleep'):  # Mock sleep
                result = make_openrouter_request(
                    api_key='test-key',
                    payload={'model': 'openai/gpt-3.5-turbo', 'messages': []},
                    timeout=30,
                    retry_attempts=3,
                    retry_delay=1
                )

                assert result['choices'][0]['message']['content'] == 'Success after connection retry'
                mock_module.warn.assert_called()


if __name__ == '__main__':
    pytest.main([__file__])