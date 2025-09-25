#!/usr/bin/env python3
"""
Pytest configuration for rtfm.ai_modules tests
"""

import sys
import os
from unittest.mock import Mock

# Add the plugins directory to Python path
plugins_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'plugins', 'modules'))
if plugins_path not in sys.path:
    sys.path.insert(0, plugins_path)

# Mock all external dependencies that might not be available in CI
def mock_modules():
    """Mock external modules that are not available in test environment"""
    modules_to_mock = [
        'ansible',
        'ansible.module_utils',
        'ansible.module_utils.basic',
        'google',
        'google.generativeai',
        'google.api_core',
        'google.api_core.exceptions',
        'requests',
    ]

    for module_name in modules_to_mock:
        if module_name not in sys.modules:
            sys.modules[module_name] = Mock()

# Apply mocks when conftest is imported
mock_modules()

# Mock AnsibleModule specifically
class MockAnsibleModule:
    def __init__(self, argument_spec, supports_check_mode=False):
        self.params = {}
        self.check_mode = False

    def fail_json(self, **kwargs):
        raise Exception(f"Module failed: {kwargs}")

    def exit_json(self, **kwargs):
        pass

    def warn(self, msg):
        pass

# Replace AnsibleModule with our mock
if 'ansible.module_utils.basic' in sys.modules:
    sys.modules['ansible.module_utils.basic'].AnsibleModule = MockAnsibleModule