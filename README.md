# rtfm.ai_modules - Ansible Collection for AI APIs

[![Test Collection](https://github.com/overlordtm/ansible-ai-modules/actions/workflows/test.yml/badge.svg)](https://github.com/overlordtm/ansible-ai-modules/actions/workflows/test.yml)
[![Release Collection](https://github.com/overlordtm/ansible-ai-modules/actions/workflows/release.yml/badge.svg)](https://github.com/overlordtm/ansible-ai-modules/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An Ansible collection providing modules for interacting with various AI APIs including Google Gemini and OpenRouter (which provides access to GPT, Claude, and other models).

## Features

- **Gemini Module**: Direct integration with Google's Gemini API
  - Safety settings configuration
  - Multiple model support (Gemini 1.5 Flash, Pro, etc.)
  - Token usage tracking
  - Retry logic for rate limits

- **OpenRouter Module**: Access to multiple AI providers through OpenRouter
  - Support for OpenAI GPT models
  - Support for Anthropic Claude models
  - Support for Google models via OpenRouter
  - System message support
  - Frequency and presence penalty controls

## Installation

### From Source
```bash
git clone https://github.com/overlordtm/ansible-ai-modules.git
cd ansible-ai-modules
ansible-galaxy collection build
ansible-galaxy collection install rtfm-ai_modules-*.tar.gz
```

### Dependencies
```bash
pip install requests google-generativeai
```

## Quick Start

### Gemini Example
```yaml
- name: Analyze security report with Gemini
  rtfm.ai_modules.gemini:
    api_key: "{{ lookup('env', 'GEMINI_API_KEY') }}"
    prompt: "Summarize this security scan: {{ scan_output }}"
    model_name: "gemini-1.5-flash-latest"
    temperature: 0.5
    max_output_tokens: 1024
  register: analysis

- debug:
    msg: "{{ analysis.result.text }}"
```

### OpenRouter Example
```yaml
- name: Analyze logs with Claude via OpenRouter
  rtfm.ai_modules.openrouter:
    api_key: "{{ lookup('env', 'OPENROUTER_API_KEY') }}"
    model: "anthropic/claude-3-sonnet"
    system_message: "You are a security analyst."
    prompt: "Analyze these logs for threats: {{ log_data }}"
    temperature: 0.3
    max_tokens: 2048
  register: analysis

- debug:
    msg: "{{ analysis.result.text }}"
```

## API Keys

Get your API keys from:
- **Gemini**: [Google AI Studio](https://makersuite.google.com/app/apikey)
- **OpenRouter**: [OpenRouter Dashboard](https://openrouter.ai/keys)

Set them as environment variables:
```bash
export GEMINI_API_KEY="your_gemini_key"
export OPENROUTER_API_KEY="your_openrouter_key"
```

## Testing

The collection includes comprehensive tests:

```bash
# Install test dependencies
pip install -r requirements.txt

# Run unit tests (no API calls)
pytest tests/unit/

# Run manual tests (requires API keys)
ansible-playbook tests/test_gemini.yml
ansible-playbook tests/test_openrouter.yml

# Run integration tests
ansible-test integration
```

See [tests/README_TESTING.md](tests/README_TESTING.md) for detailed testing instructions.

## Available Modules

### `rtfm.ai_modules.gemini`

Interact with Google's Gemini API.

**Parameters:**
- `api_key` (required): Your Google API key
- `prompt` (required): The text prompt to send
- `model_name`: Gemini model to use (default: `gemini-1.5-flash-latest`)
- `temperature`: Randomness control (0.0-1.0)
- `max_output_tokens`: Maximum response length
- `safety_settings`: Content safety configuration
- `raw_json_output`: Return full API response (boolean)

### `rtfm.ai_modules.openrouter`

Interact with multiple AI providers through OpenRouter.

**Parameters:**
- `api_key` (required): Your OpenRouter API key
- `prompt` (required): The text prompt to send
- `model`: Model to use (default: `openai/gpt-3.5-turbo`)
- `system_message`: System context message
- `temperature`: Randomness control (0.0-2.0)
- `max_tokens`: Maximum response length
- `frequency_penalty`: Penalty for token repetition
- `presence_penalty`: Penalty for topic repetition
- `raw_json_output`: Return full API response (boolean)

## Use Cases

- **Security Analysis**: Process security scan outputs, log analysis
- **Documentation**: Generate summaries, explanations
- **Code Review**: Analyze code for issues or improvements
- **Data Processing**: Extract insights from text data
- **Report Generation**: Create structured reports from raw data

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for your changes
4. Ensure all tests pass
5. Submit a pull request

### Development Setup
```bash
git clone https://github.com/overlordtm/ansible-ai-modules.git
cd ansible-ai-modules
pip install -r requirements.txt
```

### Running Tests in CI

The collection includes GitHub Actions workflows that:
- Run unit tests on multiple Python versions
- Run integration tests with real API calls (when secrets are available)
- Perform security scanning
- Build and validate the collection

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Security

- API keys are handled securely with `no_log: true`
- No sensitive data is logged or exposed
- Rate limiting and retry logic included
- Input validation on all parameters

## Support

- Documentation: Check module docstrings and examples
- Issues: [GitHub Issues](https://github.com/overlordtm/ansible-ai-modules/issues)
- Testing: See [tests/README_TESTING.md](tests/README_TESTING.md)

## Changelog

### v0.0.1 (Current)
- Initial release
- Gemini module with full API support
- OpenRouter module with multi-provider support
- Comprehensive test suite
- CI/CD pipeline with GitHub Actions