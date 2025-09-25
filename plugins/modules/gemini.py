#!/usr/bin/python

# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Your Name <your_email@example.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: gemini
short_description: Interact with Google Gemini API
description:
  - This module submits prompts to the specified Google Gemini model using the google-generativeai library.
  - It allows configuration of the API key, model, generation parameters (temperature, token limits, etc.), and safety settings.
  - It supports Jinja2 templating within the prompt string, allowing dynamic content injection from Ansible variables.
  - Includes basic retry logic for rate limiting errors (ResourceExhausted).
  - Can return the raw API response structure as a dictionary for detailed inspection.
version_added: "1.1.0" # Updated version to reflect new feature
author:
  - Andraz Vrhovec (@overlordtm)
options:
  api_key:
    description:
      - Your Google Cloud API Key for Gemini.
    type: str
    required: true
    no_log: true # Important for sensitive data
  prompt:
    description:
      - The text prompt to send to the Gemini model.
      - Can contain Jinja2 templating which Ansible will render before passing to the module.
    type: str
    required: true
  model_name:
    description:
      - The name of the Gemini model to use.
      - Examples include 'gemini-1.5-flash-latest', 'gemini-1.5-pro-latest', 'gemini-pro'.
    type: str
    default: 'gemini-1.5-flash-latest'
  temperature:
    description:
      - Controls randomness. Lower values are more deterministic, higher values are more creative.
      - Must be between 0.0 and 1.0.
    type: float
    required: False
  top_p:
    description:
      - The cumulative probability cutoff for token selection. Lower values focus on more probable tokens.
      - Must be between 0.0 and 1.0.
    type: float
    required: False
  top_k:
    description:
      - Sample from the K most likely next tokens at each step.
      - Must be a positive integer.
    type: int
    required: False
  max_output_tokens:
    description:
      - The maximum number of tokens to generate in the response.
    type: int
    required: False
  candidate_count:
    description:
      - The number of response candidates to generate. Currently only 1 is well-supported for text.
    type: int
    default: 1
  safety_settings:
    description:
      - A dictionary defining content safety thresholds.
      - Keys are categories (e.g., 'HARM_CATEGORY_HATE_SPEECH') and values are thresholds (e.g., 'BLOCK_MEDIUM_AND_ABOVE').
      - See Google AI documentation for valid categories and thresholds.
      - If not provided, the API's default safety settings will be used.
    type: dict
    required: False
    # Example:
    # safety_settings:
    #   HARM_CATEGORY_HARASSMENT: BLOCK_ONLY_HIGH
    #   HARM_CATEGORY_HATE_SPEECH: BLOCK_MEDIUM_AND_ABOVE
    #   HARM_CATEGORY_SEXUALLY_EXPLICIT: BLOCK_LOW_AND_ABOVE
    #   HARM_CATEGORY_DANGEROUS_CONTENT: BLOCK_NONE
  retry_attempts:
    description:
      - Number of times to retry the API call if a rate limit error (ResourceExhausted) occurs.
    type: int
    default: 3
  retry_delay:
    description:
      - Delay in seconds between retry attempts for rate limit errors.
    type: int
    default: 5
  raw_json_output:
    description:
      - If set to true, the module will return the complete, raw API response structure as a dictionary under the 'raw_response' key,
        instead of the simplified 'result' structure. Error messages (if any) will still be included at the top level.
    type: bool
    default: False
requirements:
  - google-generativeai python library (>=0.5.0 recommended)
notes:
  - Ensure the 'google-generativeai' library is installed on the Ansible control node (or target if delegated). `pip install google-generativeai`
  - Ansible's Jinja2 templating engine processes the 'prompt' argument *before* it is passed to this module. Include your Ansible variables directly in the prompt string in your playbook (e.g., `prompt: "Summarize this report: {{ linpeas_output }}"`).
  - Check the Google AI documentation for the latest model names and parameter behaviors.
  - When `raw_json_output: true`, the structure of the returned data changes significantly. Refer to the `RETURN` section and Google AI documentation for the structure of the raw response.
'''

EXAMPLES = r'''
- name: Summarize Linpeas output using Gemini (Default output)
  hosts: localhost
  gather_facts: no
  vars:
    linpeas_raw_output: "{{ lookup('file', 'linpeas_report.txt') }}"

  tasks:
    - name: Summarize security report with Gemini
      gemini:
        api_key: "{{ lookup('env', 'GEMINI_API_KEY') }}"
        model_name: "gemini-1.5-flash-latest"
        prompt: |
          Summarize the key security findings from this report:
          ```
          {{ linpeas_raw_output }}
          ```
        temperature: 0.5
        max_output_tokens: 1024
      register: gemini_summary

    - name: Display Gemini Summary
      debug:
        msg: "{{ gemini_summary.result.text }}"

- name: Analyze combined reports (Raw JSON output)
  hosts: localhost
  gather_facts: no
  vars:
    report1: "{{ lookup('file', 'report1.txt') }}"
    report2: "{{ lookup('file', 'report2.txt') }}"
    gemini_api_key_env: "{{ lookup('env', 'GEMINI_API_KEY') }}"

  tasks:
    - name: Check if API key is set
      fail:
        msg: "GEMINI_API_KEY environment variable is not set."
      when: gemini_api_key_env | length == 0

    - name: Generate combined security analysis (get raw response)
      gemini:
        api_key: "{{ gemini_api_key_env }}"
        model_name: "gemini-1.5-pro-latest"
        prompt: |
          Analyze these reports for vulnerabilities:
          Report 1: {{ report1 }}
          Report 2: {{ report2 }}
        max_output_tokens: 2048
        temperature: 0.3
        raw_json_output: true # Enable raw output
      register: combined_analysis_raw

    - name: Show Raw Response Structure
      debug:
        var: combined_analysis_raw.raw_response # Access the raw response key

    - name: Access text from raw response (example)
      debug:
        msg: "{{ combined_analysis_raw.raw_response.candidates[0].content.parts[0].text }}" # Example: accessing text from raw structure
      when:
        - combined_analysis_raw.raw_response is defined
        - combined_analysis_raw.raw_response.candidates is defined and combined_analysis_raw.raw_response.candidates | length > 0
        - combined_analysis_raw.raw_response.candidates[0].content is defined
        - combined_analysis_raw.raw_response.candidates[0].content.parts is defined and combined_analysis_raw.raw_response.candidates[0].content.parts | length > 0
        - combined_analysis_raw.raw_response.candidates[0].content.parts[0].text is defined

'''

RETURN = r'''
result:
  description: The simplified result object representing the primary outcome of the Gemini API call.
  type: dict
  returned: always, *unless* `raw_json_output` is true.
  contains:
    text:
      description: The generated text response from the Gemini model. May be None if generation failed or was blocked.
      type: str
      sample: "The security report indicates critical vulnerabilities..."
    prompt_feedback: # Note: This is a simplified version of prompt_feedback
      description: Feedback regarding the safety of the prompt (simplified).
      type: dict
      contains:
        block_reason:
          description: The reason the prompt was blocked, if any.
          type: str
          sample: "SAFETY"
        safety_ratings:
          description: List of safety ratings for the prompt (simplified).
          type: list
          elements: dict
          sample: [{"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "probability": "NEGLIGIBLE"}]
    candidates: # Note: This is a simplified version of candidates
      description: A list of generated candidates (usually just one for text prompts) (simplified).
      type: list
      elements: dict
      # Simplified content structure
      sample: [{"content": {"parts": [{"text": "..."}]}, "finish_reason": "STOP", "safety_ratings": [...]}]
    usage_metadata: # Note: This is a simplified version of usage_metadata
       description: Metadata about token usage for the request (simplified).
       type: dict
       contains:
         prompt_token_count:
           description: Number of tokens in the prompt.
           type: int
         candidates_token_count:
           description: Number of tokens in the generated candidates.
           type: int
         total_token_count:
           description: Total number of tokens.
           type: int
    error:
      description: An error message if the generation failed after retries or was blocked (prompt or content).
      type: str
      returned: on failure or block (in default mode)

raw_response:
  description: The complete, raw dictionary representation of the Gemini API response object.
  type: dict
  returned: only when `raw_json_output` is true.
  # The structure here is dictated by the google-generativeai library's object structure
  # converted to Python dicts. It typically mirrors the underlying protobuf structure.
  contains:
    prompt_feedback:
      description: Full prompt feedback object structure.
      type: dict # Structure as returned by convert_prompt_feedback_to_dict
    candidates:
      description: Full list of candidate object structures.
      type: list
      elements: dict # Structure as returned by convert_candidate_to_dict
    usage_metadata:
      description: Full usage metadata object structure.
      type: dict # Structure as returned by convert_usage_metadata_to_dict
    # Note: The 'text' convenience property might or might not be present here,
    # depending on the original object structure and if content was extractable.
    # Access text via candidates[0].content.parts[0].text is more reliable on raw.
'''

import time
import traceback

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    # We might need json_format for robust protobuf to dict conversion
    # from google.protobuf import json_format # Not strictly needed if objects have .to_dict() or similar wrappers
    HAS_GEMINI_LIB = True
except ImportError:
    HAS_GEMINI_LIB = False

from ansible.module_utils.basic import AnsibleModule

# Define module globally so helper functions can access it for logging/failing
module = None

def convert_safety_settings_input_to_api(safety_settings_input):
    """Converts user-provided safety settings dict to the format required by the API."""
    safety_settings_api = []
    if safety_settings_input:
        if not isinstance(safety_settings_input, dict):
             module.fail_json(msg="Parameter 'safety_settings' must be a dictionary.")
        for key, value in safety_settings_input.items():
            if not isinstance(key, str) or not isinstance(value, str):
                module.fail_json(msg=f"Invalid safety_settings format. Both category ('{key}') and threshold ('{value}') must be strings.")
            try:
                 # Check if category and threshold are valid enums/strings known by the library
                 category_enum = genai.types.HarmCategory[key]
                 threshold_enum = genai.types.HarmBlockThreshold[value]
                 safety_settings_api.append({
                     'category': category_enum,
                     'threshold': threshold_enum,
                 })
            except KeyError as e:
                 module.fail_json(msg=f"Invalid safety category ('{key}') or threshold ('{value}'). Check Google AI documentation for valid values. Error: {e}")
            except Exception as e:
                 module.fail_json(msg=f"Unexpected error processing safety setting '{key}': {str(e)}")
    return safety_settings_api


def convert_prompt_feedback_to_dict(prompt_feedback_obj):
    """Converts the PromptFeedback object to a dictionary suitable for Ansible."""
    if not prompt_feedback_obj:
        return None

    feedback_dict = {}
    # block_reason is an enum, get its name string
    if hasattr(prompt_feedback_obj, 'block_reason'):
         feedback_dict['block_reason'] = prompt_feedback_obj.block_reason.name if prompt_feedback_obj.block_reason else None

    # safety_ratings is a list of SafetyRating objects; convert each to dict
    safety_ratings_list = []
    if hasattr(prompt_feedback_obj, 'safety_ratings') and prompt_feedback_obj.safety_ratings:
        for rating in prompt_feedback_obj.safety_ratings:
             # SafetyRating objects usually have a to_dict() method or similar
             if hasattr(rating, 'to_dict'):
                 try:
                     safety_ratings_list.append(rating.to_dict())
                 except Exception as e:
                     module.warn(f"Failed to convert SafetyRating to dict using .to_dict(): {e}") # Use module.warn for non-fatal issues
                     # Fallback attempt manual conversion
                     rating_dict = {}
                     if hasattr(rating, 'category'):
                         rating_dict['category'] = rating.category.name if rating.category else None
                     if hasattr(rating, 'probability'):
                         rating_dict['probability'] = rating.probability.name if rating.probability else None
                     if hasattr(rating, 'blocked'):
                         rating_dict['blocked'] = rating.blocked
                     safety_ratings_list.append(rating_dict)
             else:
                 module.warn(f"SafetyRating object has no .to_dict() method.") # Use module.warn
                 # Manual conversion if no to_dict()
                 rating_dict = {}
                 if hasattr(rating, 'category'):
                     rating_dict['category'] = rating.category.name if rating.category else None
                 if hasattr(rating, 'probability'):
                     rating_dict['probability'] = rating.probability.name if rating.probability else None
                 if hasattr(rating, 'blocked'):
                      rating_dict['blocked'] = rating.blocked
                 safety_ratings_list.append(rating_dict)

    feedback_dict['safety_ratings'] = safety_ratings_list

    return feedback_dict


def convert_usage_metadata_to_dict(usage_metadata_obj):
    """Converts UsageMetadata object to a dictionary."""
    if not usage_metadata_obj:
        return None

    usage_dict = {}
    if hasattr(usage_metadata_obj, 'prompt_token_count'):
        usage_dict['prompt_token_count'] = usage_metadata_obj.prompt_token_count
    if hasattr(usage_metadata_obj, 'candidates_token_count'):
        usage_dict['candidates_token_count'] = usage_metadata_obj.candidates_token_count
    if hasattr(usage_metadata_obj, 'total_token_count'):
        usage_dict['total_token_count'] = usage_metadata_obj.total_token_count

    # Add other usage metadata fields if they become available/relevant
    # e.g., billable_character_count

    return usage_dict


def convert_candidate_to_dict(candidate_obj):
    """Converts Candidate object to a dictionary."""
    if not candidate_obj:
        return None

    cand_dict = {}

    # Content object might need manual conversion if it's not a simple dict/protobuf
    if hasattr(candidate_obj, 'content'):
        content_dict = {}
        if hasattr(candidate_obj.content, 'parts'):
             parts_list = []
             for part in candidate_obj.content.parts:
                 # Assuming parts are text-based for now
                 part_dict = {}
                 if hasattr(part, 'text'):
                     part_dict['text'] = part.text
                 # Add other part types if needed (e.g., inline_data for images)
                 parts_list.append(part_dict)
             content_dict['parts'] = parts_list

        if hasattr(candidate_obj.content, 'role'):
            content_dict['role'] = candidate_obj.content.role

        cand_dict['content'] = content_dict


    # finish_reason is an enum
    if hasattr(candidate_obj, 'finish_reason'):
        cand_dict['finish_reason'] = candidate_obj.finish_reason.name if candidate_obj.finish_reason else None

    # safety_ratings is a list of SafetyRating objects, convert each
    safety_ratings_list = []
    if hasattr(candidate_obj, 'safety_ratings') and candidate_obj.safety_ratings:
         for rating in candidate_obj.safety_ratings:
             if hasattr(rating, 'to_dict'):
                 try:
                     safety_ratings_list.append(rating.to_dict())
                 except Exception as e:
                     module.warn(f"Failed to convert SafetyRating in candidate to dict using .to_dict(): {e}")
                     # Fallback attempt manual conversion
                     rating_dict = {}
                     if hasattr(rating, 'category'):
                         rating_dict['category'] = rating.category.name if rating.category else None
                     if hasattr(rating, 'probability'):
                         rating_dict['probability'] = rating.probability.name if rating.probability else None
                     if hasattr(rating, 'blocked'):
                         rating_dict['blocked'] = rating.blocked
                     safety_ratings_list.append(rating_dict)

             else:
                 module.warn(f"SafetyRating object in candidate has no .to_dict() method.")
                 # Manual conversion if no to_dict()
                 rating_dict = {}
                 if hasattr(rating, 'category'):
                     rating_dict['category'] = rating.category.name if rating.category else None
                 if hasattr(rating, 'probability'):
                     rating_dict['probability'] = rating.probability.name if rating.probability else None
                 if hasattr(rating, 'blocked'):
                      rating_dict['blocked'] = rating.blocked
                 safety_ratings_list.append(rating_dict)

    cand_dict['safety_ratings'] = safety_ratings_list # Add the list even if empty

    if hasattr(candidate_obj, 'token_count'): # May not be present on all candidate objects
         cand_dict['token_count'] = candidate_obj.token_count
    if hasattr(candidate_obj, 'index'):
         cand_dict['index'] = candidate_obj.index

    # Add other relevant candidate fields if needed
    # e.g., finish_message

    return cand_dict


def run_module():
    module_args = dict(
        api_key=dict(type='str', required=True, no_log=True),
        prompt=dict(type='str', required=True),
        model_name=dict(type='str', default='gemini-1.5-flash-latest'),
        temperature=dict(type='float', required=False),
        top_p=dict(type='float', required=False),
        top_k=dict(type='int', required=False),
        max_output_tokens=dict(type='int', required=False),
        candidate_count=dict(type='int', default=1),
        safety_settings=dict(type='dict', required=False),
        retry_attempts=dict(type='int', default=3),
        retry_delay=dict(type='int', default=5),
        raw_json_output=dict(type='bool', default=False),
    )

    global module # Make module available to helper functions
    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=False # Gemini API calls have side effects (cost, quotas)
    )

    if not HAS_GEMINI_LIB:
        module.fail_json(msg="The 'google-generativeai' Python library is required. Please install it: pip install google-generativeai")

    api_key = module.params['api_key']
    prompt = module.params['prompt']
    model_name = module.params['model_name']
    temperature = module.params['temperature']
    top_p = module.params['top_p']
    top_k = module.params['top_k']
    max_output_tokens = module.params['max_output_tokens']
    candidate_count = module.params['candidate_count']
    safety_settings_input = module.params['safety_settings']
    retry_attempts = module.params['retry_attempts']
    retry_delay = module.params['retry_delay']
    raw_json_output = module.params['raw_json_output']


    # --- Parameter Validation ---
    if temperature is not None and not (0.0 <= temperature <= 1.0):
         module.fail_json(msg="Parameter 'temperature' must be between 0.0 and 1.0")
    if top_p is not None and not (0.0 <= top_p <= 1.0):
         module.fail_json(msg="Parameter 'top_p' must be between 0.0 and 1.0")
    if top_k is not None and top_k is not None and top_k <= 0: # Check is not None again for clarity
         module.fail_json(msg="Parameter 'top_k' must be a positive integer")
    if max_output_tokens is not None and max_output_tokens <= 0:
         module.fail_json(msg="Parameter 'max_output_tokens' must be a positive integer")
    if candidate_count <= 0:
         module.fail_json(msg="Parameter 'candidate_count' must be a positive integer")

    safety_settings_api = convert_safety_settings_input_to_api(safety_settings_input)

    # --- Configure Gemini ---
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        module.fail_json(msg=f"Failed to configure Gemini API: {str(e)}")

    # --- Prepare Generation Config ---
    gen_config_dict = {}
    if temperature is not None:
        gen_config_dict['temperature'] = temperature
    if top_p is not None:
        gen_config_dict['top_p'] = top_p
    if top_k is not None:
        gen_config_dict['top_k'] = top_k
    if max_output_tokens is not None:
        gen_config_dict['max_output_tokens'] = max_output_tokens
    if candidate_count is not None:
        gen_config_dict['candidate_count'] = candidate_count

    generation_config = genai.types.GenerationConfig(**gen_config_dict) if gen_config_dict else None

    # --- Initialize Model ---
    try:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=generation_config,
            safety_settings=safety_settings_api # Pass validated settings or []
        )
    except Exception as e:
        module.fail_json(msg=f"Failed to initialize Gemini model '{model_name}': {str(e)}")


    # --- Call Gemini API with Retry Logic ---
    attempts = 0
    response = None
    last_exception = None

    while attempts <= retry_attempts:
        attempts += 1
        try:
            response = model.generate_content(prompt)

            # --- Convert Response Objects to Dicts ---
            # Do this conversion regardless of raw_json_output, as helper functions
            # are useful and we might need converted parts even in default mode.
            response_prompt_feedback = convert_prompt_feedback_to_dict(getattr(response, 'prompt_feedback', None))
            response_usage_metadata = convert_usage_metadata_to_dict(getattr(response, 'usage_metadata', None))
            response_candidates = [convert_candidate_to_dict(c) for c in getattr(response, 'candidates', [])]

            # --- Handle Prompt Blocks ---
            if response_prompt_feedback and response_prompt_feedback.get('block_reason'):
                 generation_error = f"Prompt blocked due to {response_prompt_feedback.get('block_reason')}. Safety Ratings: {response_prompt_feedback.get('safety_ratings')}"
                 # If prompt is blocked, we *always* fail the task, but include the feedback
                 fail_result = {
                    'prompt_feedback': response_prompt_feedback,
                    'usage_metadata': response_usage_metadata,
                    'candidates': response_candidates, # Include candidates even if prompt blocked? API might not return them.
                    'error': generation_error
                 }
                 # If raw_json_output is true, structure the fail_result differently?
                 # No, failing is an exception state, the fail_json structure is standard.
                 module.fail_json(msg=generation_error, result=fail_result)


            # --- Handle Candidate Issues (Content Blocks, Bad Finish) ---
            candidate_errors = []
            generated_text = None # Initialize text field for default output

            if response_candidates:
                 # Usually only one candidate with current API for text
                 candidate_dict = response_candidates[0] # Use the converted dict

                 finish_reason = candidate_dict.get('finish_reason')
                 # Note: finish_reason might be 'SAFETY' for content blocks too, check safety_ratings
                 if finish_reason not in ('STOP', 'MAX_TOKENS', 'SAFETY'): # Added SAFETY finish reason
                     candidate_errors.append(f"Candidate finished unexpectedly: {finish_reason}")
                 elif finish_reason == 'SAFETY':
                      # If finish_reason is SAFETY, check safety_ratings for details
                     candidate_errors.append(f"Candidate generation stopped due to safety reasons.")


                 # Check safety ratings on the candidate for explicit blocks
                 candidate_safety_ratings = candidate_dict.get('safety_ratings', [])
                 content_blocked = False
                 for rating in candidate_safety_ratings:
                     # Check if the rating indicates a block
                     if rating.get('probability') and rating.get('probability') != 'NEGLIGIBLE':
                         # More robust check using the 'blocked' flag if available
                         if rating.get('blocked', False) or rating.get('probability') in ('MEDIUM', 'HIGH'):
                             candidate_errors.append(f"Candidate content blocked for {rating.get('category')} (Probability: {rating.get('probability')}).")
                             content_blocked = True # Flag that content was blocked
                             # Don't break, gather all block reasons if multiple categories are blocked

                 # Attempt to extract text if no content block was detected
                 if not content_blocked:
                     # Use the convenience accessor first, as it handles joining parts
                     try:
                         # Access original response object's text property
                         generated_text = response.text
                     except ValueError as ve:
                         # ValueError often means content was blocked or is empty/non-text
                         # This could be a fallback check if safety_ratings didn't explicitly flag it
                         # Or if the response structure is unexpected
                         candidate_errors.append(f"Could not extract text from candidate (potential content issue): {str(ve)}")
                     except Exception as e:
                          # Catch unexpected errors during text access
                          candidate_errors.append(f"Unexpected error extracting text: {str(e)}")
                 else:
                     # If content was blocked based on safety_ratings, text will be None
                     generated_text = None


            # --- Prepare Final Return ---
            if raw_json_output:
                # Return the raw, converted response structure
                raw_response_dict = {
                    'prompt_feedback': response_prompt_feedback,
                    'candidates': response_candidates,
                    'usage_metadata': response_usage_metadata,
                    # Optionally add the convenience text field here too if extracted successfully
                    'text': generated_text # Include extracted text even in raw output
                }

                # Add candidate errors to the top level error message if raw output is requested,
                # but the task itself still succeeds.
                return_params = {'changed': True, 'raw_response': raw_response_dict}
                if candidate_errors:
                     return_params['error'] = "; ".join(candidate_errors)
                     # Note: Task is marked changed, but not failed, if only candidate content is problematic.
                     # This aligns with returning the raw response for inspection.

                module.exit_json(**return_params)

            else:
                # Return the simplified result structure (default behavior)
                result = {
                    'text': generated_text,
                    'prompt_feedback': response_prompt_feedback,
                    'candidates': response_candidates, # Include simplified candidate info
                    'usage_metadata': response_usage_metadata,
                }

                if candidate_errors:
                    # Add candidate errors to the result
                    result['error'] = "; ".join(candidate_errors)
                    # For content blocks, we return the error but the task succeeds
                    # This allows inspecting the safety ratings etc.
                    module.exit_json(changed=True, result=result)
                else:
                    # Success! No prompt block or candidate errors
                    module.exit_json(changed=True, result=result)

            # Break the loop if successful (exit_json stops execution, so this is effectively unreachable)
            break

        except google_exceptions.ResourceExhausted as e:
            last_exception = e
            if attempts > retry_attempts:
                module.fail_json(msg=f"Gemini API rate limit exceeded after {retry_attempts} retries: {str(e)}",
                                 exception=traceback.format_exc())
            module.warn(f"Rate limit exceeded, retrying in {retry_delay} seconds... (Attempt {attempts}/{retry_attempts})")
            # Wait before retrying
            time.sleep(retry_delay)
            continue # Go to next attempt

        except google_exceptions.InvalidArgument as e:
            # Often due to bad model name, parameters, or potentially safety settings format
             module.fail_json(msg=f"Gemini API Invalid Argument: {str(e)}. Check model name, parameters, and safety settings.",
                              exception=traceback.format_exc())
        except google_exceptions.GoogleAPIError as e:
             # Catch other Google API errors (permissions, server errors, etc.)
             last_exception = e
             if attempts > retry_attempts:
                 module.fail_json(msg=f"Gemini API Error after {retry_attempts} retries: {str(e)}",
                                  exception=traceback.format_exc())
             # Consider retrying some non-ResourceExhausted errors? For now, only retry rate limits and transient server errors.
             if isinstance(e, google_exceptions.InternalServerError) or \
                isinstance(e, google_exceptions.ServiceUnavailable):
                 module.warn(f"Transient API error encountered, retrying in {retry_delay} seconds... (Attempt {attempts}/{retry_attempts}) Error: {str(e)}")
                 time.sleep(retry_delay)
                 continue
             else:
                 # Fail fast on auth errors, invalid args etc. not explicitly handled
                  module.fail_json(msg=f"Gemini API Error: {str(e)}", exception=traceback.format_exc())

        except Exception as e:
            # Catch-all for unexpected errors (e.g., library bugs, network issues not caught by google-api-core)
             module.fail_json(msg=f"An unexpected error occurred: {str(e)}",
                              exception=traceback.format_exc())

    # This part should theoretically not be reached if exit_json or fail_json is always called
    module.fail_json(msg="Gemini module finished unexpectedly without success or specific failure.")


def main():
    run_module()

if __name__ == '__main__':
    main()