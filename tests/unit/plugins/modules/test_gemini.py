#!/usr/bin/env python3

# Import the module to test
import sys

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the plugins/modules directory to the Python path
modules_path = Path(__file__).parent / '../../../../plugins/modules'
modules_path = modules_path.resolve()
if str(modules_path) not in sys.path:
    sys.path.insert(0, str(modules_path))

# Create mock exception classes that inherit from Exception
class MockGoogleAPIError(Exception):
    """Mock Google API Error that can be caught"""
    pass

class MockResourceExhausted(Exception):
    """Mock Resource Exhausted Error that can be caught"""
    pass

class MockInternalServerError(Exception):
    """Mock Internal Server Error that can be caught"""
    pass

class MockRetryError(Exception):
    """Mock Retry Error that can be caught"""
    pass

# Mock ansible and google modules before importing
sys.modules['ansible'] = Mock()
sys.modules['ansible.module_utils'] = Mock()
sys.modules['ansible.module_utils.basic'] = Mock()
sys.modules['google'] = Mock()
sys.modules['google.generativeai'] = Mock()
sys.modules['google.api_core'] = Mock()

# Create a proper mock for exceptions module
mock_exceptions = Mock()
mock_exceptions.GoogleAPIError = MockGoogleAPIError
mock_exceptions.ResourceExhausted = MockResourceExhausted
mock_exceptions.InternalServerError = MockInternalServerError
mock_exceptions.RetryError = MockRetryError
sys.modules['google.api_core.exceptions'] = mock_exceptions

# Now import the module
try:
    from gemini import convert_safety_settings_input_to_api, run_module
except ImportError as e:
    pytest.skip(f"Could not import gemini module: {e}")


class TestGeminiModule:
    """Unit tests for Gemini module"""

    def test_parameter_validation_temperature_too_high(self):
        """Test that temperature > 1.0 fails validation"""
        with patch('gemini.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            mock_instance.params = {
                'api_key': 'test-key',
                'prompt': 'test prompt',
                'model_name': 'gemini-1.5-flash-latest',
                'temperature': 1.5,
                'top_p': None,
                'top_k': None,
                'max_output_tokens': None,
                'candidate_count': 1,
                'safety_settings': None,
                'retry_attempts': 3,
                'retry_delay': 5,
                'raw_json_output': False
            }

            # Mock fail_json to raise an exception to stop execution early
            mock_instance.fail_json.side_effect = SystemExit("Parameter validation failed")

            with patch('gemini.HAS_GEMINI_LIB', True):
                try:
                    run_module()
                except SystemExit:
                    pass  # Expected behavior when fail_json is called

                mock_instance.fail_json.assert_called_once()
                call_args = mock_instance.fail_json.call_args[1]
                assert 'temperature' in call_args['msg']

    def test_parameter_validation_top_k_negative(self):
        """Test that negative top_k fails validation"""
        with patch('gemini.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            mock_instance.params = {
                'api_key': 'test-key',
                'prompt': 'test prompt',
                'model_name': 'gemini-1.5-flash-latest',
                'temperature': None,
                'top_p': None,
                'top_k': -5,
                'max_output_tokens': None,
                'candidate_count': 1,
                'safety_settings': None,
                'retry_attempts': 3,
                'retry_delay': 5,
                'raw_json_output': False
            }

            # Mock fail_json to raise an exception to stop execution early
            mock_instance.fail_json.side_effect = SystemExit("Parameter validation failed")

            with patch('gemini.HAS_GEMINI_LIB', True):
                try:
                    run_module()
                except SystemExit:
                    pass  # Expected behavior when fail_json is called

                mock_instance.fail_json.assert_called_once()
                call_args = mock_instance.fail_json.call_args[1]
                assert 'top_k' in call_args['msg']

    def test_safety_settings_conversion_valid(self):
        """Test valid safety settings conversion"""
        with patch('gemini.module'), patch('gemini.genai') as mock_genai:
            # Mock the enum access
            mock_genai.types.HarmCategory = {
                'HARM_CATEGORY_HARASSMENT': 'HARM_CATEGORY_HARASSMENT',
                'HARM_CATEGORY_HATE_SPEECH': 'HARM_CATEGORY_HATE_SPEECH'
            }
            mock_genai.types.HarmBlockThreshold = {
                'BLOCK_ONLY_HIGH': 'BLOCK_ONLY_HIGH',
                'BLOCK_MEDIUM_AND_ABOVE': 'BLOCK_MEDIUM_AND_ABOVE'
            }

            input_settings = {
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_ONLY_HIGH',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_MEDIUM_AND_ABOVE'
            }

            result = convert_safety_settings_input_to_api(input_settings)

            assert len(result) == 2
            assert result[0]['category'] == 'HARM_CATEGORY_HARASSMENT'
            assert result[0]['threshold'] == 'BLOCK_ONLY_HIGH'

    def test_safety_settings_conversion_invalid_category(self):
        """Test invalid safety settings category"""
        with patch('gemini.module') as mock_module:
            mock_module.fail_json = Mock()

            with patch('gemini.genai') as mock_genai:
                # Mock KeyError for invalid category
                def side_effect_category(self, key):
                    if key == 'INVALID_CATEGORY':
                        raise KeyError(f"'{key}'")
                    return 'VALID_CATEGORY'

                def side_effect_threshold(self, key):
                    return 'VALID_THRESHOLD'

                mock_genai.types.HarmCategory.__getitem__ = side_effect_category
                mock_genai.types.HarmBlockThreshold.__getitem__ = side_effect_threshold

                input_settings = {
                    'INVALID_CATEGORY': 'BLOCK_ONLY_HIGH'
                }

                convert_safety_settings_input_to_api(input_settings)

                mock_module.fail_json.assert_called_once()
                call_args = mock_module.fail_json.call_args[1]
                assert 'Invalid safety category' in call_args['msg']

    def test_missing_gemini_library(self):
        """Test behavior when google-generativeai library is not available"""
        with patch('gemini.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance

            # Mock fail_json to raise an exception to stop execution early
            mock_instance.fail_json.side_effect = SystemExit("Library missing")

            with patch('gemini.HAS_GEMINI_LIB', False):
                try:
                    run_module()
                except SystemExit:
                    pass  # Expected behavior when fail_json is called

                mock_instance.fail_json.assert_called_once()
                call_args = mock_instance.fail_json.call_args[1]
                assert 'google-generativeai' in call_args['msg']

    @patch('gemini.genai')
    def test_successful_generation(self, mock_genai):
        """Test successful content generation"""
        with patch('gemini.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            mock_instance.params = {
                'api_key': 'test-key',
                'prompt': 'test prompt',
                'model_name': 'gemini-1.5-flash-latest',
                'temperature': 0.7,
                'top_p': None,
                'top_k': None,
                'max_output_tokens': 100,
                'candidate_count': 1,
                'safety_settings': None,
                'retry_attempts': 3,
                'retry_delay': 5,
                'raw_json_output': False
            }

            # Mock successful generation
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model

            mock_response = Mock()
            mock_response.text = 'Generated response text'
            mock_response.prompt_feedback = None
            mock_response.usage_metadata = Mock()
            mock_response.usage_metadata.total_token_count = 50
            mock_response.candidates = [Mock()]

            mock_model.generate_content.return_value = mock_response

            # Mock conversion functions
            with patch('gemini.convert_prompt_feedback_to_dict', return_value=None):  # noqa: SIM117
                with patch('gemini.convert_usage_metadata_to_dict', return_value={'total_token_count': 50}):
                    with patch('gemini.convert_candidate_to_dict', return_value={'finish_reason': 'STOP'}):
                        with patch('gemini.HAS_GEMINI_LIB', True):
                            run_module()

                            mock_instance.exit_json.assert_called_once()
                            call_args = mock_instance.exit_json.call_args[1]
                            assert call_args['changed'] is True
                            assert call_args['result']['text'] == 'Generated response text'

    @patch('gemini.genai')
    def test_prompt_blocked(self, mock_genai):
        """Test prompt blocked by safety filters"""
        with patch('gemini.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            mock_instance.params = {
                'api_key': 'test-key',
                'prompt': 'dangerous prompt',
                'model_name': 'gemini-1.5-flash-latest',
                'temperature': None,
                'top_p': None,
                'top_k': None,
                'max_output_tokens': None,
                'candidate_count': 1,
                'safety_settings': None,
                'retry_attempts': 3,
                'retry_delay': 5,
                'raw_json_output': False
            }

            # Mock model setup
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model

            # Mock blocked response
            mock_response = Mock()
            mock_response.prompt_feedback = Mock()
            mock_response.usage_metadata = None
            mock_response.candidates = []

            mock_model.generate_content.return_value = mock_response

            # Mock conversion to return blocked prompt feedback
            blocked_feedback = {
                'block_reason': 'SAFETY',
                'safety_ratings': [{'category': 'HARM_CATEGORY_HATE_SPEECH', 'probability': 'HIGH'}]
            }

            with patch('gemini.convert_prompt_feedback_to_dict', return_value=blocked_feedback):  # noqa: SIM117
                with patch('gemini.convert_usage_metadata_to_dict', return_value=None):
                    with patch('gemini.convert_candidate_to_dict', return_value=None):
                        with patch('gemini.HAS_GEMINI_LIB', True):
                            run_module()

                            # Should have called fail_json (might be called multiple times)
                            assert mock_instance.fail_json.called
                            # Check if any call mentions blocked content
                            calls = mock_instance.fail_json.call_args_list
                            assert any('blocked' in str(call).lower() for call in calls)

    @patch('gemini.genai')
    def test_rate_limit_retry(self, mock_genai):
        """Test rate limit retry mechanism"""
        with patch('gemini.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            mock_instance.warn = Mock()
            mock_instance.params = {
                'api_key': 'test-key',
                'prompt': 'test prompt',
                'model_name': 'gemini-1.5-flash-latest',
                'temperature': None,
                'top_p': None,
                'top_k': None,
                'max_output_tokens': None,
                'candidate_count': 1,
                'safety_settings': None,
                'retry_attempts': 2,
                'retry_delay': 1,
                'raw_json_output': False
            }

            # Mock model setup
            mock_model = Mock()
            mock_genai.GenerativeModel.return_value = mock_model

            mock_success_response = Mock()
            mock_success_response.text = 'Success after retry'
            mock_success_response.prompt_feedback = None
            mock_success_response.usage_metadata = Mock()
            mock_success_response.candidates = [Mock()]

            # Create actual exception instance
            rate_limit_error = MockResourceExhausted("Rate limit exceeded")
            mock_model.generate_content.side_effect = [rate_limit_error, mock_success_response]

            with patch('gemini.google_exceptions.ResourceExhausted', MockResourceExhausted):  # noqa: SIM117
                with patch('gemini.google_exceptions.GoogleAPIError', MockGoogleAPIError):  # noqa: SIM117
                    with patch('gemini.convert_prompt_feedback_to_dict', return_value=None):
                        with patch('gemini.convert_usage_metadata_to_dict', return_value={}):
                            with patch('gemini.convert_candidate_to_dict', return_value={'finish_reason': 'STOP'}):
                                with patch('gemini.time.sleep'):  # Mock sleep
                                    with patch('gemini.HAS_GEMINI_LIB', True):
                                        run_module()

                                        # Should have warned about rate limit
                                        mock_instance.warn.assert_called()

    def test_invalid_model_name(self):
        """Test invalid model name handling"""
        with patch('gemini.AnsibleModule') as mock_module:
            mock_instance = Mock()
            mock_module.return_value = mock_instance
            mock_instance.params = {
                'api_key': 'test-key',
                'prompt': 'test prompt',
                'model_name': 'invalid-model',
                'temperature': None,
                'top_p': None,
                'top_k': None,
                'max_output_tokens': None,
                'candidate_count': 1,
                'safety_settings': None,
                'retry_attempts': 3,
                'retry_delay': 5,
                'raw_json_output': False
            }

            # Mock fail_json to raise an exception to stop execution early
            mock_instance.fail_json.side_effect = SystemExit("Invalid model")

            with patch('gemini.genai') as mock_genai:
                # Mock model initialization failure
                mock_genai.GenerativeModel.side_effect = Exception("Invalid model name")

                with patch('gemini.google_exceptions.ResourceExhausted', MockResourceExhausted):  # noqa: SIM117
                    with patch('gemini.google_exceptions.GoogleAPIError', MockGoogleAPIError):  # noqa: SIM117
                        with patch('gemini.HAS_GEMINI_LIB', True):
                            try:
                                run_module()
                            except SystemExit:
                                pass  # Expected behavior when fail_json is called

                            mock_instance.fail_json.assert_called_once()
                            call_args = mock_instance.fail_json.call_args[1]
                            assert 'model' in call_args['msg'].lower()


if __name__ == '__main__':
    pytest.main([__file__])
