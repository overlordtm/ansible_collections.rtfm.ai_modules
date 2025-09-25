# Testing Guide for rtfm.ai_modules Collection

This guide explains how to test the Ansible modules in the `rtfm.ai_modules` collection.

## Prerequisites

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

You'll need API keys for the services you want to test:

```bash
# For Gemini module
export GEMINI_API_KEY="your_gemini_api_key_here"

# For OpenRouter module
export OPENROUTER_API_KEY="your_openrouter_api_key_here"
```

**Getting API Keys:**
- **Gemini**: Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **OpenRouter**: Get your API key from [OpenRouter Dashboard](https://openrouter.ai/keys)

## Testing Methods

### 1. Quick Manual Testing

Use the simple test playbooks to quickly verify modules work:

```bash
# Test Gemini module
ansible-playbook tests/test_gemini.yml

# Test OpenRouter module
ansible-playbook tests/test_openrouter.yml

# Compare both modules side-by-side
ansible-playbook tests/test_both.yml
```

**What these tests do:**
- Basic functionality tests
- Parameter validation tests
- Error handling tests
- Raw JSON output tests
- Model comparison (for test_both.yml)

### 2. Integration Testing

Run comprehensive integration tests using ansible-test:

```bash
# Run all integration tests
ansible-test integration

# Run tests for specific modules
ansible-test integration gemini
ansible-test integration openrouter

# Run with specific Python version
ansible-test integration --python 3.9
```

**What integration tests cover:**
- Parameter validation edge cases
- API error handling
- Safety settings (Gemini)
- System messages (OpenRouter)
- Timeout and retry logic
- Different model configurations

### 3. Unit Testing

Run unit tests with mocked API responses:

```bash
# Run all unit tests
pytest tests/unit/

# Run specific module tests
pytest tests/unit/plugins/modules/test_gemini.py
pytest tests/unit/plugins/modules/test_openrouter.py

# Run with coverage
pytest tests/unit/ --cov=plugins/modules
```

**What unit tests cover:**
- Parameter validation logic
- Response parsing
- Error handling paths
- Retry mechanisms
- Safety settings conversion (Gemini)

## Test Structure

```
tests/
├── README_TESTING.md           # This file
├── inventory                   # Test inventory file
├── test_gemini.yml            # Manual Gemini tests
├── test_openrouter.yml        # Manual OpenRouter tests
├── test_both.yml              # Comparison tests
├── integration/               # Integration tests
│   └── targets/
│       ├── gemini/
│       │   └── tasks/main.yml
│       └── openrouter/
│           └── tasks/main.yml
└── unit/                      # Unit tests
    └── plugins/
        └── modules/
            ├── test_gemini.py
            └── test_openrouter.py
```

## Environment Configuration

The collection includes configuration files:

- `ansible.cfg` - Configures Ansible for testing
- `requirements.txt` - Python dependencies
- `tests/inventory` - Simple localhost inventory

## Testing Scenarios

### Basic Functionality
- Simple prompt/response cycle
- Token usage reporting
- Model selection

### Parameter Validation
- Temperature ranges (0.0-1.0 for Gemini, 0.0-2.0 for OpenRouter)
- Token limits
- Invalid model names
- Missing required parameters

### Error Handling
- Invalid API keys
- Network timeouts
- Rate limiting (429 errors)
- Server errors (5xx)
- Model not found errors

### Advanced Features
- **Gemini**: Safety settings, raw JSON output, different models
- **OpenRouter**: System messages, frequency/presence penalties, multiple providers

## Troubleshooting

### Common Issues

**"Module not found" errors:**
```bash
# Ensure you're in the collection directory
cd /path/to/rtfm.ai_modules
# Or set ANSIBLE_COLLECTIONS_PATH
export ANSIBLE_COLLECTIONS_PATH=/path/to/collections
```

**API key issues:**
```bash
# Verify environment variables are set
echo $GEMINI_API_KEY
echo $OPENROUTER_API_KEY
```

**Permission errors:**
```bash
# Ensure inventory file is readable
chmod 644 tests/inventory
```

**Import errors in unit tests:**
```bash
# Install test dependencies
pip install pytest pytest-mock
```

### Testing Without API Keys

You can run unit tests without API keys since they use mocked responses:

```bash
pytest tests/unit/
```

Integration and manual tests require real API keys.

## Continuous Integration

For automated testing, set up environment variables in your CI system:

```yaml
# Example for GitHub Actions
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
```

## Writing New Tests

### Adding Manual Tests
Edit the test playbooks in `tests/` to add new scenarios.

### Adding Integration Tests
Add new test tasks to `tests/integration/targets/*/tasks/main.yml`.

### Adding Unit Tests
Add test methods to the test classes in `tests/unit/plugins/modules/`.

## Test Coverage Goals

- ✅ Basic module functionality
- ✅ Parameter validation
- ✅ Error handling
- ✅ API response parsing
- ✅ Retry logic
- ✅ Different model configurations
- ✅ Raw output modes
- ✅ Safety features

## Performance Testing

For load testing or rate limit testing:

```bash
# Run the same test multiple times
for i in {1..5}; do
    ansible-playbook tests/test_gemini.yml
done
```

## Security Testing

Both modules handle API keys securely:
- Keys are marked with `no_log: true`
- Keys are not logged or printed
- Test with invalid keys to verify error handling

## Getting Help

If you encounter issues:

1. Check the logs: `tail -f ansible.log`
2. Run with increased verbosity: `ansible-playbook -vvv tests/test_gemini.yml`
3. Verify API keys are valid and have sufficient credits
4. Check the module documentation in the source files

## Contributing Tests

When contributing new features:

1. Add unit tests for logic changes
2. Add integration tests for new parameters
3. Update manual tests with examples
4. Test error conditions and edge cases