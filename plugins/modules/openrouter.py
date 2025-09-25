#!/usr/bin/python

# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Andraz Vrhovec <andraz@rtfm.si>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)



DOCUMENTATION = r"""
---
module: openrouter
short_description: Interact with OpenRouter API
description:
  - This module submits prompts to various AI models via the OpenRouter API.
  - It allows configuration of the API key, model selection, generation parameters (temperature, token limits, etc.).
  - It supports Jinja2 templating within the prompt string, allowing dynamic content injection from Ansible variables.
  - Includes basic retry logic for rate limiting errors (429 status codes).
  - Can return the raw API response structure as a dictionary for detailed inspection.
version_added: "1.0.0"
author:
  - Andraz Vrhovec (@overlordtm)
options:
  api_key:
    description:
      - Your OpenRouter API Key.
    type: str
    required: true
    no_log: true
  prompt:
    description:
      - The text prompt to send to the model.
      - Can contain Jinja2 templating which Ansible will render before passing to the module.
    type: str
    required: true
  model:
    description:
      - The model to use for generation.
      - Examples include 'openai/gpt-4', 'anthropic/claude-3-sonnet', 'google/gemini-pro', etc.
    type: str
    default: 'openai/gpt-3.5-turbo'
  system_message:
    description:
      - Optional system message to set the context for the conversation.
    type: str
    required: false
  temperature:
    description:
      - Controls randomness. Lower values are more deterministic, higher values are more creative.
      - Must be between 0.0 and 2.0.
    type: float
    required: false
  top_p:
    description:
      - The cumulative probability cutoff for token selection. Lower values focus on more probable tokens.
      - Must be between 0.0 and 1.0.
    type: float
    required: false
  max_tokens:
    description:
      - The maximum number of tokens to generate in the response.
    type: int
    required: false
  frequency_penalty:
    description:
      - Penalty for repeating tokens. Values between -2.0 and 2.0.
    type: float
    required: false
  presence_penalty:
    description:
      - Penalty for using tokens that have already appeared. Values between -2.0 and 2.0.
    type: float
    required: false
  retry_attempts:
    description:
      - Number of times to retry the API call if a rate limit error (429) occurs.
    type: int
    default: 3
  retry_delay:
    description:
      - Delay in seconds between retry attempts for rate limit errors.
    type: int
    default: 5
  raw_json_output:
    description:
      - If set to true, the module will return the complete, raw API response structure as a dictionary under the 'raw_response' key.
    type: bool
    default: false
  timeout:
    description:
      - Request timeout in seconds.
    type: int
    default: 30
requirements:
  - requests python library
notes:
  - Ensure the 'requests' library is installed on the Ansible control node. `pip install requests`
  - Ansible's Jinja2 templating engine processes the 'prompt' argument *before* it is passed to this module.
  - Check the OpenRouter documentation for the latest model names and parameter behaviors.
  - When `raw_json_output: true`, the structure of the returned data changes significantly.
"""

EXAMPLES = r"""
- name: Summarize security report using OpenRouter
  hosts: localhost
  gather_facts: no
  vars:
    security_report: "{{ lookup('file', 'security_report.txt') }}"

  tasks:
    - name: Summarize security report with GPT-4
      openrouter:
        api_key: "{{ lookup('env', 'OPENROUTER_API_KEY') }}"
        model: "openai/gpt-4"
        prompt: |
          Summarize the key security findings from this report:
          ```
          {{ security_report }}
          ```
        temperature: 0.5
        max_tokens: 1024
      register: summary

    - name: Display summary
      debug:
        msg: "{{ summary.result.text }}"

- name: Analyze logs with Claude (Raw JSON output)
  hosts: localhost
  gather_facts: no
  vars:
    log_data: "{{ lookup('file', 'system.log') }}"

  tasks:
    - name: Analyze logs with Claude
      openrouter:
        api_key: "{{ lookup('env', 'OPENROUTER_API_KEY') }}"
        model: "anthropic/claude-3-sonnet"
        system_message: "You are a security analyst reviewing system logs."
        prompt: |
          Analyze these logs for security issues:
          {{ log_data }}
        max_tokens: 2048
        temperature: 0.3
        raw_json_output: true
      register: analysis_raw

    - name: Show raw response structure
      debug:
        var: analysis_raw.raw_response

- name: Compare models on same prompt
  hosts: localhost
  gather_facts: no
  tasks:
    - name: Get GPT-4 response
      openrouter:
        api_key: "{{ lookup('env', 'OPENROUTER_API_KEY') }}"
        model: "openai/gpt-4"
        prompt: "Explain quantum computing in simple terms"
        temperature: 0.7
      register: gpt4_response

    - name: Get Claude response
      openrouter:
        api_key: "{{ lookup('env', 'OPENROUTER_API_KEY') }}"
        model: "anthropic/claude-3-sonnet"
        prompt: "Explain quantum computing in simple terms"
        temperature: 0.7
      register: claude_response

    - name: Compare responses
      debug:
        msg: |
          GPT-4: {{ gpt4_response.result.text }}

          Claude: {{ claude_response.result.text }}
"""

RETURN = r"""
result:
  description: The simplified result object representing the primary outcome of the OpenRouter API call.
  type: dict
  returned: always, unless `raw_json_output` is true.
  contains:
    text:
      description: The generated text response from the model.
      type: str
      sample: "The security report indicates critical vulnerabilities..."
    model:
      description: The model that was used for generation.
      type: str
      sample: "openai/gpt-4"
    usage:
      description: Token usage information.
      type: dict
      contains:
        prompt_tokens:
          description: Number of tokens in the prompt.
          type: int
        completion_tokens:
          description: Number of tokens in the completion.
          type: int
        total_tokens:
          description: Total number of tokens used.
          type: int
    error:
      description: An error message if the generation failed.
      type: str
      returned: on failure

raw_response:
  description: The complete, raw dictionary representation of the OpenRouter API response.
  type: dict
  returned: only when `raw_json_output` is true.
  contains:
    choices:
      description: List of generated completions.
      type: list
    usage:
      description: Token usage information.
      type: dict
    model:
      description: The model used.
      type: str
    created:
      description: Unix timestamp of when the completion was created.
      type: int
"""

import time
import traceback

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from ansible.module_utils.basic import AnsibleModule

module = None


def make_openrouter_request(api_key, payload, timeout, retry_attempts, retry_delay):
    """Make a request to the OpenRouter API with retry logic."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/overlordtm/ansible-ai-modules",
        "X-Title": "Ansible AI Modules",
    }

    attempts = 0
    last_exception = None

    while attempts <= retry_attempts:
        attempts += 1
        try:
            response = requests.post(
                url, headers=headers, json=payload, timeout=timeout
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limit
                if attempts > retry_attempts:
                    module.fail_json(
                        msg=f"OpenRouter API rate limit exceeded after {retry_attempts} retries"
                    )
                module.warn(
                    f"Rate limit exceeded, retrying in {retry_delay} seconds... (Attempt {attempts}/{retry_attempts})"
                )
                time.sleep(retry_delay)
                continue
            elif response.status_code == 401:
                module.fail_json(
                    msg="OpenRouter API authentication failed. Check your API key."
                )
            elif response.status_code == 400:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get(
                        "message", "Bad request"
                    )
                except:  # noqa: E722
                    error_msg = response.text
                module.fail_json(msg=f"OpenRouter API bad request: {error_msg}")
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get(
                        "message", f"HTTP {response.status_code}"
                    )
                except:  # noqa: E722
                    error_msg = f"HTTP {response.status_code}: {response.text}"

                if response.status_code >= 500 and attempts <= retry_attempts:
                    module.warn(
                        f"Server error encountered, retrying in {retry_delay} seconds... (Attempt {attempts}/{retry_attempts}) Error: {error_msg}"
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    module.fail_json(msg=f"OpenRouter API error: {error_msg}")

        except requests.exceptions.Timeout as e:
            last_exception = e
            if attempts > retry_attempts:
                module.fail_json(
                    msg=f"OpenRouter API request timeout after {retry_attempts} retries: {str(e)}"
                )
            module.warn(
                f"Request timeout, retrying in {retry_delay} seconds... (Attempt {attempts}/{retry_attempts})"
            )
            time.sleep(retry_delay)
            continue

        except requests.exceptions.ConnectionError as e:
            last_exception = e
            if attempts > retry_attempts:
                module.fail_json(
                    msg=f"OpenRouter API connection error after {retry_attempts} retries: {str(e)}"
                )
            module.warn(
                f"Connection error, retrying in {retry_delay} seconds... (Attempt {attempts}/{retry_attempts})"
            )
            time.sleep(retry_delay)
            continue

        except Exception as e:
            module.fail_json(
                msg=f"Unexpected error during OpenRouter API request: {str(e)}",
                exception=traceback.format_exc(),
            )

    module.fail_json(
        msg=f"OpenRouter API request failed after {retry_attempts} retries. Last error: {str(last_exception)}"
    )


def run_module():
    module_args = {
        "api_key": {"type": "str", "required": True, "no_log": True},
        "prompt": {"type": "str", "required": True},
        "model": {"type": "str", "default": "openai/gpt-3.5-turbo"},
        "system_message": {"type": "str", "required": False},
        "temperature": {"type": "float", "required": False},
        "top_p": {"type": "float", "required": False},
        "max_tokens": {"type": "int", "required": False},
        "frequency_penalty": {"type": "float", "required": False},
        "presence_penalty": {"type": "float", "required": False},
        "retry_attempts": {"type": "int", "default": 3},
        "retry_delay": {"type": "int", "default": 5},
        "raw_json_output": {"type": "bool", "default": False},
        "timeout": {"type": "int", "default": 30},
    }

    global module
    module = AnsibleModule(argument_spec=module_args, supports_check_mode=False)

    if not HAS_REQUESTS:
        module.fail_json(
            msg="The 'requests' Python library is required. Please install it: pip install requests"
        )

    # Get parameters
    api_key = module.params["api_key"]
    prompt = module.params["prompt"]
    model_name = module.params["model"]
    system_message = module.params["system_message"]
    temperature = module.params["temperature"]
    top_p = module.params["top_p"]
    max_tokens = module.params["max_tokens"]
    frequency_penalty = module.params["frequency_penalty"]
    presence_penalty = module.params["presence_penalty"]
    retry_attempts = module.params["retry_attempts"]
    retry_delay = module.params["retry_delay"]
    raw_json_output = module.params["raw_json_output"]
    timeout = module.params["timeout"]

    # Parameter validation
    if temperature is not None and not (0.0 <= temperature <= 2.0):
        module.fail_json(msg="Parameter 'temperature' must be between 0.0 and 2.0")
    if top_p is not None and not (0.0 <= top_p <= 1.0):
        module.fail_json(msg="Parameter 'top_p' must be between 0.0 and 1.0")
    if max_tokens is not None and max_tokens <= 0:
        module.fail_json(msg="Parameter 'max_tokens' must be a positive integer")
    if frequency_penalty is not None and not (-2.0 <= frequency_penalty <= 2.0):
        module.fail_json(
            msg="Parameter 'frequency_penalty' must be between -2.0 and 2.0"
        )
    if presence_penalty is not None and not (-2.0 <= presence_penalty <= 2.0):
        module.fail_json(
            msg="Parameter 'presence_penalty' must be between -2.0 and 2.0"
        )
    if timeout <= 0:
        module.fail_json(msg="Parameter 'timeout' must be a positive integer")

    # Build messages array
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    # Build payload
    payload = {"model": model_name, "messages": messages}

    # Add optional parameters
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if frequency_penalty is not None:
        payload["frequency_penalty"] = frequency_penalty
    if presence_penalty is not None:
        payload["presence_penalty"] = presence_penalty

    # Make the API request
    response_data = make_openrouter_request(
        api_key, payload, timeout, retry_attempts, retry_delay
    )

    # Process response
    if raw_json_output:
        module.exit_json(changed=True, raw_response=response_data)
    else:
        # Extract the main text response
        try:
            text_response = response_data["choices"][0]["message"]["content"]
            usage_info = response_data.get("usage", {})

            result = {
                "text": text_response,
                "model": response_data.get("model", model_name),
                "usage": {
                    "prompt_tokens": usage_info.get("prompt_tokens", 0),
                    "completion_tokens": usage_info.get("completion_tokens", 0),
                    "total_tokens": usage_info.get("total_tokens", 0),
                },
            }

            module.exit_json(changed=True, result=result)

        except (KeyError, IndexError) as e:
            module.fail_json(
                msg=f"Unexpected response structure from OpenRouter API: {str(e)}",
                raw_response=response_data,
            )


def main():
    run_module()


if __name__ == "__main__":
    main()
