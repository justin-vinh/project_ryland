"""
------------------------------------------------------------------------------
Author:         Justin Vinh
Collaborators:  Thomas Sounack
Institution:    Dana-Farber Cancer Institute
Working Groups: Lindvall & Rhee Labs
Parent Package: Project Ryland
Creation Date:  2025.10.06
Last Modified:  2026.05.12

Purpose:
Contain the functions necessary to pull the proper LLM prompt and
then connect to the OpenAI API to run the promopt on given data
------------------------------------------------------------------------------
"""

import glob
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel, Field

import openai
import pandas as pd
import yaml
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from environs import Env
from openai import AzureOpenAI, OpenAI, RateLimitError
from pydantic import ValidationError
from scipy.cluster.hierarchy import complete
from tqdm import tqdm
from json_repair import repair_json

from .llm_config import llm_model_meta
from .llm_tracker import update_run_summary
from project_ryland import __version__

# --- Configure logging ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clear existing handlers
logger.handlers = []

# File handler
log_filename = "llm_tracking.log"
file_handler = logging.FileHandler(log_filename)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S"
))
logger.addHandler(file_handler)

# Silence noisy libraries
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Silence Azure identity noise (IMDS / credential probing logs)
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
# --- Configure logging ---


# FUNCTIONS
# -----------------------------------------------------------------------------
def summarize_llm_runs(
    log_path: str | Path = "llm_tracking.log",
    csv_path: str | Path = "llm_run_summaries.csv",
    legacy=False
) -> pd.DataFrame:
    """
    Parse Project Ryland llm_tracking.log files and maintain a structured
    CSV summary of completed LLM runs.
    """

    # Use the func from llm_tracker.py
    df = update_run_summary(
        log_path=log_path,
        csv_path=csv_path,
        legacy=legacy
    )

    return df


def retrieve_llm_prompt(
        prompt_text: str = None,
        use_prompt_gallery: bool = False,
        prompt_name: str = None,
        prompt_gallery_path: str = None) -> Dict[str, str]:
    """
    Retrieve a specific LLM prompt from the centralized prompt gallery.
    Looks up the prompt_name in the YAML registry, loads the associated .txt file,
    and returns the full text. Optionally returns YAML metadata as well.
    """

    # Use the prompt gallery if available and specified to do so
    if use_prompt_gallery:
        # define the prompt gallery root and prompt config file
        if prompt_gallery_path is None:
            print('[ERROR] Using prompt gallery but gallery path not provided.')
        gallery_dir = Path(prompt_gallery_path)
        prompt_config_path = gallery_dir / "config_llm_prompts.yaml"

        # Open reference YAML file and handle potential errors
        try:
            with open(prompt_config_path, 'r') as f:
                prompts = yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f'[ERROR] Could not find prompt config file: {prompt_config_path}. '
                f'Check file or path to prompt gallery.'
            )
        except yaml.YAMLError as e:
            raise ValueError(f'Error parsing prompt config file: {e}')

        # Validate prompt name before moving forward
        if prompt_name not in prompts:
            raise KeyError(f'[ERROR] Prompt {prompt_name} not found in {prompt_config_path}')

        # Retrieve prompt metadata
        prompt_meta = prompts[prompt_name]
        prompt_filename = gallery_dir / prompt_meta['filename']

        # Based on the reference file and prompt name, load prompt (and handle errors)
        try:
            with open(prompt_filename, 'r') as f:
                prompt_text = f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f'[ERROR] Prompt file not found: {prompt_filename}')

    else:
    # If the user inserts *only* the prompt text without using the prompt gallery
    # feature, use the inputted text and create dummy metadata
        prompt_text = prompt_text
        prompt_meta = {'filename': 'Filename (Not Applicable)',
                       'description': 'Description Unknown',
                       'author': 'Author Unknown',
                       'date': 'Date Unknown'}

    # Return the prompt and the metadata as a dict
    return {'prompt_text': prompt_text, 'metadata': prompt_meta}


def retrieve_llm_prompt_with_inserted_variables(
    prompt_name: str = None,
    prompt_text: str = None,
    use_prompt_gallery: bool = False,
    prompt_gallery_path: str = None,
    user_prompt_vars: Dict[str, str] = None) -> Dict[str, str]:
    """
    Retrive a stored prompt template, check for any placeholder variables
    (denoted {variable} in the prompt), and dynamically fill them in with
    user-provided values
    """
    # Retrieve the prompt (format: {'prompt_text': <string>, 'metadata': <dict>})
    prompt = retrieve_llm_prompt(
        prompt_text=prompt_text,
        use_prompt_gallery=use_prompt_gallery,
        prompt_gallery_path=prompt_gallery_path,
        prompt_name=prompt_name
    )

    # Find what variable(s) are in the prompt:
    text = prompt['prompt_text']
    prompt_vars = re.findall(r'{{(.*?)}}', text)
    if prompt_vars:
        print(f'[INFO] Placeholder variables are found in the prompt: {prompt_vars}')
    else:
        print(f'[INFO] No placeholder variables found in the prompt')

    # If placeholders exist but no user variables provided
    if prompt_vars and not user_prompt_vars:
        print('[WARNING] Prompt contains placeholder variables '
              'but no user variables were provided.')
        print(f'[WARNING] These placeholders still need values: {prompt_vars}')
        return prompt

    # If all these prompt variables are not accounted for in the user-defined
    # variables, throw up a warning
    all_vars_accounted = True
    for var in prompt_vars:
        if var not in user_prompt_vars:
            all_vars_accounted = False
            print(f'[ERROR] Variable "{var}" in given prompt NOT defined by user.'
                  f' MUST FIX')
    if not all_vars_accounted:
        return

    # Replace prompt placeholder variables with the user-defined variables
    if prompt_vars:
        user_prompt_vars_clean = {
            k: ', '.join(v) if isinstance(v, list) else v
            for k, v in user_prompt_vars.items()
        }
        # Replace double braces with single braces
        prompt['prompt_text'] = prompt['prompt_text'].replace('{{', '{').replace('}}', '}')
        prompt['prompt_text'] = prompt['prompt_text'].format(**user_prompt_vars_clean)
        print(f'\n[INFO] Prompt successfully retrieved + '
              f'placeholder variables replaced by user-defined values:')
        for k, v in user_prompt_vars_clean.items():
            print(f'[INFO] Placeholder:\t\t\t{k} \n[INFO] User value(s):\t\t{v}')
        print('')
    else:
        print(f'[INFO] Prompt successfully retrieved\n')

    return prompt


class LLMCostTracker:
    def __init__(self, model_name):
        """Cost tracker for LLM API usage"""
        self.input_cost = 0
        self.output_cost = 0
        self.total_cost = 0
        # Initiate known per-one-million token costs based on model name
        model_meta = llm_model_meta[model_name]
        self.input_1M_token_cost = model_meta['cost_per_1M_token_input']
        self.output_1M_token_cost = model_meta['cost_per_1M_token_output']
        self.cost_unit = model_meta['cost_unit']

    def update_cost(self, llm_output_meta) -> Dict[str, float]:
        """Tracks cumulative costs and returns costs in a dict format"""
        # Calculate costs
        input_tokens = llm_output_meta.usage.prompt_tokens
        output_tokens = llm_output_meta.usage.completion_tokens
        input_cost = self.input_1M_token_cost * input_tokens / 1e6
        output_cost = self.output_1M_token_cost * output_tokens / 1e6

        # Update costs
        self.input_cost += input_cost
        self.output_cost += output_cost
        self.total_cost = self.input_cost + self.output_cost

        # Handle special case if costs < $0.01
        self.input_cost = 0.01 if self.input_cost < 0.01 else self.input_cost
        self.output_cost = 0.01 if self.output_cost < 0.01 else self.output_cost
        self.total_cost = 0.01 if self.total_cost < 0.01 else self.total_cost

        # Add cumulative costs to a dict
        tracker_output = {
            "Input": self.input_cost,
            "Output": self.output_cost,
            "Total": self.total_cost,
            "Unit": self.cost_unit
        }
        # logging.info(tracker_output)  # Uncomment if you want cum. costs per row

        return tracker_output

    def nicely_show_cost(self, as_string=False) -> Dict[str, str]:
        """Returns formatted cumulative costs for logging/display"""

        # If specified, return output as a string, else return as a dict
        if as_string:
            output = (
                f'"Input": {self.cost_unit}{self.input_cost:.2f} | '
                f'"Output": {self.cost_unit}{self.output_cost:.2f} | '
                f'"Total": {self.cost_unit}{self.total_cost:.2f}')
        else:
            output = {
                "Input": f'{self.cost_unit}{self.input_cost:.2f}',
                "Output": f'{self.cost_unit}{self.output_cost:.2f}',
                "Total": f'{self.cost_unit}{self.total_cost:.2f}'
            }

        return output


class LLM_wrapper:
    def __init__(
        self,
        model_name: str,
        endpoint: str = None,
        entra_scope: str = None,
        api_key: str = None,
        base_url: str = None,
        env_abs_path: str = None):
        """
        Initialize an LLM_wrapper client for Azure OpenAI (GPT4DFCI) or public OpenAI.

        This constructor detects and configures API credentials from either explicit
        arguments or environment variables loaded from a ``.env`` file. It supports:

        - Azure OpenAI (via endpoint + Entra scope token provider)
        - Public OpenAI API (via API key)

        If no credentials are passed directly, environment variables are loaded using
        ``environs.Env``. An optional absolute path to a ``.env`` file may be provided.

        :param model_name: Name of the LLM model to use for chat completions.
                           Must exist in ``llm_model_meta`` for cost tracking.
        :type model_name: str

        :param endpoint: Azure OpenAI endpoint base URL. If provided together with
                         ``entra_scope``, Azure authentication is used.
        :type endpoint: str | None

        :param entra_scope: Azure Entra ID scope used to obtain a bearer token for
                            Azure OpenAI authentication.
        :type entra_scope: str | None

        :param api_key: Public OpenAI API key. If provided (and Azure variables
                             are not), standard OpenAI authentication is used.
        :type api_key: str | None

        :param env_abs_path: Absolute path to a ``.env`` file to load if one is not
                             found automatically in the working directory.
        :type env_abs_path: pathlib.Path | None

        :raises EnvironmentError:
            If neither Azure credentials (endpoint + entra_scope) nor an OpenAI API key
            can be found from arguments or environment variables.

        :ivar API_TYPE: Detected API backend type ("AZURE" or "OPENAI").
        :vartype API_TYPE: str

        :ivar client: Configured OpenAI client instance for the selected backend.
        :vartype client: openai.OpenAI
        """

        # Sets up the environment depending on what was read from the .env file
        if (endpoint is None and
            entra_scope is None and
            api_key is None):
            # Set up environment
            env = Env()
            try:
                env.read_env()
            except OSError:
                if env_abs_path is not None and env_abs_path.exists():
                    env.read_env(env_abs_path)
                    print("Loaded .env from", env_abs_path)
                elif env_abs_path is None:
                    print('[ERROR] No .env file found. Please specify an absolute path')
                else:
                    print("[ERROR] No .env file found at", env_abs_path)
            sys.path.append('../')

            endpoint = env.str('ENDPOINT', None)
            entra_scope = env.str('ENTRA_SCOPE', None)
            api_key = env.str("API_TEST_KEY", None)

        # Detects which variables are present depending on whether the public OpenAI API
        # or the GPT4DFCI key is being used based on the API key values given
        self.API_TYPE = None
        if endpoint and entra_scope:
            # Detected Azure (GPT4DFCI) environment
            print(f'[INFO] Detected Azure OpenAI (GPT4DFCI) configuration')
            self.API_TYPE = "AZURE"
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                entra_scope
            )
            self.client = OpenAI(
                base_url=endpoint,
                api_key=token_provider,
            )
        elif api_key:
            # Detected standard OpenAI environment
            print(f'[INFO] Detected standard OpenAI configuration')
            self.API_TYPE = 'OPENAI'

            # Config the base url if provided, else just the API key
            if base_url:
                print(f'[INFO] Adding base URL configuration')
                self.client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                self.client = OpenAI(api_key=api_key)

        else:
            raise EnvironmentError(
                "No valid API credentials found. "
                "Please set ENDPOINT + ENTRA_SCOPE (for Azure) or "
                "API_TEST_KEY (for OpenAI Cloud)."
            )

        self.model_name = model_name

    # Set up utility functions
    # -------------------------------------------------------------------------
    @staticmethod
    def remove_strict_field(data: List[Dict[str, Any]]) \
        -> List[Dict[str, Any]]:
        """Remove unsupported "strict" fields in the schema (function dict)"""
        for item in data:
            item['function'].pop('strict', None)
        return data

    @staticmethod
    def extract_name_value(data: List[Dict[str, Any]]) -> str:
        """Extract the function name from the function dict"""
        return data[0]['function']['name']

    @staticmethod
    def load_prompt(
        use_prompt_gallery: bool = False,
        prompt_gallery_path: str = None,
        prompt_name: str = None,
        prompt_text: str = None,
        user_prompt_vars: Dict[str, str] = None,
        return_matadata: bool=False) -> str:
        """
        Load a specific prompt from the centralized prompt gallery.
        Print metadata if desired
        """
        prompt = retrieve_llm_prompt_with_inserted_variables(
            prompt_name=prompt_name,
            prompt_text=prompt_text,
            use_prompt_gallery=use_prompt_gallery,
            prompt_gallery_path=prompt_gallery_path,
            user_prompt_vars=user_prompt_vars
        )

        # States whether the prompt comes from the prompt gallery or a direct source
        if use_prompt_gallery:
            prompt_source = 'PROMPT GALLERY'
        else:
            prompt_source = 'USER DIRECTLY PROVIDED'

        # Print any prompt metadata if available
        if return_matadata:
            print(f'[INFO] Prompt Info...')
            print(f'[INFO] Prompt source: {prompt_source}')
            for key, value in prompt['metadata'].items():
                print(f'{key}: {value}')
            print('\n')
        return prompt['prompt_text']

    # Set up the API interaction
    # -------------------------------------------------------------------------
    def openai_chat_completion_response(
        self,
        prompt: str,
        input_text: str,
        format_class,
        format_class_type='pydantic'):
        """Call the Azure OpenAI API with structured response parsing"""

        # Sets up a parameter set for the chat completion response
        # Will add to this set based on API type or model type
        chat_response_params = {
            'model': self.model_name,
            'messages': [{"role": "system", "content": prompt},
                        {"role": "user", "content": input_text}],
        }

        # Sets the temperature to 0 if using any model other than gpt-5
        if 'gpt-5' not in self.model_name and 'gpt' in self.model_name:
            chat_response_params['temperature'] = 0.0

        try:
            # Uses the chat response pathway for the new DFCI Azure API
            if self.API_TYPE == 'AZURE':
                chat_response_params['response_format'] = format_class
                completion = self.client.beta.chat.completions.parse(
                    **chat_response_params
                )

                return (completion.choices[0].message.parsed,
                        completion,
                        format_class_type)

            # # Uses the chat response pathway for the public OpenAI API
            # elif self.API_TYPE == 'OPENAI':
            #     schema = [openai.pydantic_function_tool(format_class)]
            #     schema_clean = self.remove_strict_field(schema)
            #     function_name = self.extract_name_value(schema_clean)
            #
            #     chat_response_params['tools'] = schema
            #     chat_response_params['tool_choice'] = {
            #         'type': 'function',
            #         'function': {'name': function_name}
            #     }
            #
            #     # Allow only 3 retries in calling the API
            #     for attempt in range(3):
            #         completion = self.client.chat.completions.create(
            #             **chat_response_params
            #         )
            #         if completion:
            #             response = (completion.choices[0]
            #                         .message.tool_calls[0]
            #                         .function.arguments)
            #             return [json.loads(response), completion]

            elif self.API_TYPE == 'OPENAI' and format_class_type == 'json':
                try:
                    # ATTEMPT 1: native tool calling (OpenAI only)
                    schema = [openai.pydantic_function_tool(format_class)]
                    schema_clean = self.remove_strict_field(schema)
                    function_name = self.extract_name_value(schema_clean)

                    chat_response_params['tools'] = schema
                    chat_response_params['tool_choice'] = {
                        'type': 'function',
                        'function': {'name': function_name}
                    }

                    completion = self.client.chat.completions.create(
                        **chat_response_params
                    )

                    response = (completion.choices[0]
                                .message.tool_calls[0]
                                .function.arguments)

                    format_class_type = 'integrated'

                    return json.loads(response), completion, format_class_type

                except Exception:
                    format_class_type = 'integrated'
                    return None, None, format_class_type

            elif (self.API_TYPE == 'OPENAI' and
                  format_class_type == 'integrated'):
                # FALLBACK: Databricks-safe JSON prompt injection
                schema_json = format_class.model_json_schema()

                system_prompt = f"""
                You are a strict JSON generator.

                IMPORTANT: Return ONLY valid JSON.
                Do not include markdown, explanations, or code fences.

                The output MUST match this schema:
                {schema_json}
                """

                fallback_prompt = (
                    f"{prompt}\n\n{system_prompt}"
                )

                input_text = f'\n-------------------\nINPUT TEXT:\n{input_text}'

                chat_response_params['messages'] = [
                    {"role": "system", "content": fallback_prompt},
                    {"role": "user", "content": input_text}
                ]

                # remove unsupported fields if they exist
                chat_response_params.pop('tools', None)
                chat_response_params.pop('tool_choice', None)

                completion = self.client.chat.completions.create(
                    **chat_response_params
                )

                format_class_type = 'integrated'

                content = completion.choices[0].message.content

                # Remove ```json ... ``` wrappers if present
                content = re.sub(r"^```json\s*", "", content.strip())
                content = re.sub(r"^```\s*", "", content)
                content = re.sub(r"\s*```$", "", content)

                try:
                    parsed = json.loads(content)

                except json.JSONDecodeError:
                    repaired = repair_json(content)
                    parsed = json.loads(repaired)

                return parsed, completion, format_class_type

        # Handle various errors
        except openai.APIError as e:
            # Handle API error here, e.g. retry or log
            print(f"OpenAI API returned an API Error: {e}")
            pass
        except openai.APIConnectionError as e:
            # Handle connection error here
            print(f"Failed to connect to OpenAI API: {e}")
            pass
        except openai.RateLimitError as e:
            # Handle rate limit error (we recommend using exponential backoff)
            print(f"OpenAI API request exceeded rate limit: {e}")
            pass
        except ValidationError as ve:
            print(f"Pydantic validation error: {ve}")
            raise

    # Set up data handling functions
    # -------------------------------------------------------------------------
    @staticmethod
    def _atomic_save_csv(df: pd.DataFrame, path: str) -> None:
        """
        Write ``df`` to ``path`` atomically.

        A plain ``open(path, 'w')`` truncates the target file to zero bytes
        *before* the new contents are written, so an interrupt (Ctrl-C, crash,
        VPN-triggered abort) landing mid-write leaves a truncated / empty
        checkpoint and silently loses already-processed rows.

        Instead we write to a temporary file in the SAME directory, flush +
        fsync it to physical disk, then ``os.replace`` it onto the target.
        ``os.replace`` is atomic on POSIX and Windows: the checkpoint on disk
        is always either the complete previous version or the complete new
        version, never a half-written one. An interrupt mid-write just leaves a
        stray ``.tmp`` file and the real checkpoint is untouched.
        """
        import tempfile

        directory = os.path.dirname(path) or '.'
        os.makedirs(directory, exist_ok=True)

        # Same directory so os.replace is a same-filesystem (atomic) rename.
        fd, tmp_path = tempfile.mkstemp(
            dir=directory,
            prefix='.tmp_checkpoint_',
            suffix='.csv'
        )
        try:
            with os.fdopen(fd, 'w', newline='') as f:
                df.to_csv(f, index=False)
                f.flush()
                os.fsync(f.fileno())  # force OS buffers to disk
            os.replace(tmp_path, path)  # atomic swap
        except BaseException:
            # Clean up temp file on any failure/interrupt, then re-raise
            # (BaseException also covers Ctrl-C / KeyboardInterrupt).
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise

    @ staticmethod
    def load_input_file(
        input_file: str,
        text_column: str,
        sample_mode: bool = False,
        number_sampled: int = 10
        ) -> pd.DataFrame:
        """
        Load input CSV file, validate columns, and takes the first number
        of X rows specified if number_sampled if sample_mode is True
        """
        print(f'[INFO] Reading input data from \n{input_file}\n')
        df = pd.read_csv(input_file)

        if text_column not in df.columns:
            raise ValueError(f"Missing required col {text_column} in input file")

        # Return only 10 rows if sample_mode=True
        if sample_mode:
            return df.head(number_sampled)
        return df

    @ staticmethod
    def flatten_data_old(data: Dict[str, Any]) -> pd.Series:
        """
        Recursively flatten dict data. This is the old version of the function and
        remains for legacy purposes
        """
        flat = {}
        for key, value in data.items():
            if isinstance(value, dict):
                flat[f'{key}_documentation_llm'] = value.get('documentation', None)
                flat[f'{key}_text_llm'] = value.get('text', None)
            else:
                flat[key] = value
        return pd.Series(flat)

    def flatten_data(self, data: dict) -> pd.Series:
        """
        Recursively flatten nested dicts (or Pydantic objects converted to dicts)
        """
        flattened_data = {}

        def _flatten(prefix, value):
            if isinstance(value, dict):
                for k, v in value.items():
                    _flatten(f"{prefix}_{k}" if prefix else k, v)
            elif isinstance(value, list):
                # Flatten lists by JSON-stringifying
                flattened_data[prefix] = json.dumps(value)
            else:
                flattened_data[prefix] = value

        _flatten("", data)
        return pd.Series(flattened_data)

    # Set up data processing pipeline
    # -------------------------------------------------------------------------
    def process_text_data(
        self,

        text_column,
        format_class,
        input_df: pd.DataFrame = None,
        input_file_path: str = None,
        use_prompt_gallery: bool = False,

        prompt_gallery_path: str = None,
        prompt_to_get: str = None,
        prompt_text: str = None,
        user_prompt_vars = None,
        run_tag: str = None,

        sample_mode: bool = False,
        number_sampled: int = 10,
        flatten: bool = True,
        save_every: int = 5,
        output_dir: str = '../tmp',
        keep_checkpoints: bool = False,
        resume: bool = True):
        """
        Run LLM generation on a text dataset with checkpointing, cost tracking,
        and optional output flattening.

        This method loads a CSV input file, retrieves a prompt (either directly or
        from the prompt gallery), and sends each row of text to the configured LLM.
        Structured responses are stored, checkpointed periodically, optionally
        flattened into columns, and written to a timestamped output file.

        The pipeline supports resume-from-checkpoint, prompt templating with variable
        substitution, and per-run cost tracking.

        :param input_file_path: Path to the input CSV file containing text data.
        :type input_file_path: str | pathlib.Path

        :param input_df: Pandas input dataframe
        :type input_df: pd.DataFrame

        :param text_column: Name of the column containing text to send to the LLM.
        :type text_column: str

        :param format_class: Pydantic model class defining the structured response
                             schema expected from the LLM.
        :type format_class: type

        :param use_prompt_gallery: Whether to load the prompt from the prompt gallery
                                   configuration instead of using direct prompt text.
        :type use_prompt_gallery: bool

        :param prompt_gallery_path: Path to the prompt gallery directory containing
                                    the YAML config and prompt files.
        :type prompt_gallery_path: str | None

        :param prompt_to_get: Prompt name key defined in the prompt gallery YAML file.
        :type prompt_to_get: str | None

        :param prompt_text: Direct prompt text to use when not using the prompt gallery.
        :type prompt_text: str | None

        :param user_prompt_vars: Mapping of placeholder variables to replacement values
                                 for prompt templates (e.g., ``{"symptoms": [...]}``).
        :type user_prompt_vars: dict | None

        :param sample_mode: If True, only the first 10 rows of the dataset are processed.
        :type sample_mode: bool

        :param number_sampled: Sets the number of rows to sample; default=10
        :type number_sampled: int

        :param flatten: If True, flatten structured JSON outputs into separate columns
                        after generation.
        :type flatten: bool

        :param save_every: Number of processed rows between checkpoint file saves.
        :type save_every: int

        :param output_dir: Directory where checkpoint and final output CSV files
                           will be written.
        :type output_dir: str

        :param keep_checkpoints: If True, keep checkpoint files after completion.
                                 If False, they are deleted at the end.
        :type keep_checkpoints: bool

        :param resume: If True, resume from the most recent checkpoint file found
                       in ``output_dir`` for this model.
        :type resume: bool

        :returns: DataFrame containing original data plus LLM generation results and
                  any flattened output columns.
        :rtype: pandas.DataFrame

        :raises ValueError:
            If the required text column is missing from the input file.

        :raises ValidationError:
            If the LLM structured response fails Pydantic schema validation.

        :notes:
            - Output filenames include model name and timestamp.
            - A ``generation`` column stores raw structured responses as JSON strings.
            - Cost estimates are tracked using ``LLMCostTracker``.
            - Checkpoints are written as CSV and allow interrupted runs to resume.
        """

        # Generate the timestamped final output and checkpoint names

        #The run ID is the timestamp with added to-the-second precision
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_prefix = f'{self.model_name}_{timestamp}'
        checkpoint_path = os.path.join(output_dir, f'checkpoint_{base_prefix}.csv')
        final_output_path = os.path.join(output_dir, f'final_{base_prefix}.csv')

        # Ensure output dir exists
        os.makedirs(output_dir, exist_ok=True)

        # Log start of run
        # The equal sign line signals the start of a run.
        # A dashed line signals the end of a run.
        with open(log_filename, 'a') as f:
            f.write(f'====================================='
                    f'==========================================\n')

        logging.info(f'[START] New LLM generation run starting...')
        logging.info(f'[INFO] Project Ryland:           v{__version__}')
        if run_id is not None:
            logging.info(f'[INFO] Run tag:                  {run_tag}')
        logging.info(f'[INFO] Unique Run ID:            {run_id}')
        logging.info(f'[INFO] Loading LLM model:        {self.model_name}')
        if input_df is not None:
            logging.info(f'[INFO] Loading input data:       Directly loaded DataFrame')
        else: logging.info(f'[INFO] Loading input data:       {input_file_path}')

        print(f'[START] New LLM generation run starting...')
        print(f'[INFO] Project Ryland:      v{__version__}')
        print(f'[INFO] Unique Run ID:       {run_id}')
        print(f'[INFO] LLM model:           {self.model_name}')
        print(f'[INFO] Output directory:    {output_dir}')
        print(f'[INFO] Checkpoint file:     {checkpoint_path}')
        print(f'[INFO] Final output:        {final_output_path}')

        # Make sure there is either a prompt gallery with associated info,
        # or a prompt provided directly by the user. Else, throw error msg end function
        if not use_prompt_gallery and not prompt_text:
            print(f'\n[ERROR] Please provide a prompt_text.\n'
                  f'Else, use the prompt gallery function (use_prompt_gallery=True)\n'
                  f'and provide prompt_to_get and prompt_gallery_path')
            return
        if use_prompt_gallery and not prompt_gallery_path and not prompt_to_get:
            print(f'\n[ERROR] You have chosen to use the prompt gallery function:\n'
                  f'Please provide the prompt gallery path and prompt name')
            return

        # Set up checkpointing and prompts
        prompt = self.load_prompt(
            use_prompt_gallery=use_prompt_gallery,
            prompt_gallery_path=prompt_gallery_path,
            prompt_text=prompt_text,
            prompt_name=prompt_to_get,
            user_prompt_vars=user_prompt_vars,
            return_matadata=True)

        # Print and log sample_mode status and number of rows to sample
        if sample_mode:
            logging.info(f'[INFO] SAMPLE MODE STATUS:       ON')
            logging.info(f'[INFO] Number of samples:        {number_sampled}')
            print(f'[INFO] SAMPLE MODE STATUS:  ON')
            print(f'[INFO] Number of samples:   {number_sampled}')
        else:
            logging.info(f'[INFO] SAMPLE MODE STATUS:       OFF')
            print(f'[INFO] SAMPLE MODE STATUS:  OFF')

        # Log the loaded prompt name
        logging.info(f'[INFO] Loading prompt:           {prompt_to_get}\n')
        logging.info(f'[INFO] Loading prompt struct:    {format_class.__name__}')

        # Check for existing checkpoint files to resume from, else start anew
        # Work only on rows without a generation yet
        df = None
        if resume:
            existing_checkpoints = sorted(
                Path(output_dir).glob(f'checkpoint_{self.model_name}*.csv'),
                key = os.path.getmtime,
                reverse = True
            )
            if existing_checkpoints:
                latest = existing_checkpoints[0]
                print(f'[INFO] Resuming from checkpoint: {latest.name}')
                df = pd.read_csv(latest)
                if 'generation' not in df.columns:
                    df['generation'] = None
        if df is None:
            if input_df is not None:
                df = input_df.copy()
                if sample_mode:
                    df = df.head(number_sampled)
            else:
                df = self.load_input_file(
                    input_file_path,
                    text_column,
                    sample_mode=sample_mode,
                    number_sampled=number_sampled
                )
            df['generation'] = None
        df['generation'] = df['generation'].astype('object')

        # Print/log checkpoint stats
        unprocessed_df = df[df['generation'].isna()]
        logging.info(
            f"[INFO] CHECKPOINT: "
            f"Total: {len(df)}, "
            f"Processed: {len(df) - len(unprocessed_df)}, "
            f"Remaining: {len(unprocessed_df)}"
        )
        print(f"[INFO] CHECKPOINT → "
            f"Total: {len(df)}, "
            f"Processed: {len(df) - len(unprocessed_df)}, "
            f"Remaining: {len(unprocessed_df)}\n"
        )

        # Start the cost tracker and progress bar
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        start_time = datetime.now()
        print(f'[INFO] Starting LLM API call ({now})')
        cost_tracker = LLMCostTracker(self.model_name)

        # Test the waters: Figure out which gate to open for the OpenAI API type
        if self.API_TYPE =='OPENAI':
            test_text = 'This is a test'
            test_prompt = 'Give the first word in the text'
            class test_struct(BaseModel):
                test_output: str = Field(None, description='The first word in the text')
            response, completion, format_class_type = self.openai_chat_completion_response(
                test_prompt,
                test_text,
                test_struct,
                format_class_type='json'
            )
            cost_tracker.update_cost(completion)
        else:
            format_class_type = 'pydantic'

        print(f'[INFO] This prompt is using "{format_class_type}" prompt structure\n')
        logging.info(f'[INFO] Prompt Structure Type:    {format_class_type}')

        # Sets up the progress bar
        bar = tqdm(unprocessed_df.iterrows(),
                   total=len(unprocessed_df),
                   desc=f'Processing data')

        # Update with initial cost
        #bar.set_postfix(cost_tracker.nicely_show_cost())

        # Row by row, generate the LLM response to the input data
        for i, (idx, row) in enumerate(bar):
            try:
                input_text = row[text_column]
                response, completion, format_class_type = self.openai_chat_completion_response(
                    prompt,
                    input_text,
                    format_class,
                    format_class_type
                )
                # df.at[idx, 'generation'] = response

                if hasattr(response, "model_dump"):  # Pydantic v2
                    df.at[idx, "generation"] = json.dumps(response.model_dump())
                elif hasattr(response, "dict"):  # Pydantic v1
                    df.at[idx, "generation"] = json.dumps(response.dict())
                else:
                    df.at[idx, "generation"] = json.dumps(response)

                # Add the costs to the progress bar
                cost_tracker.update_cost(completion)
                bar.set_postfix(cost_tracker.nicely_show_cost())

            # Handle exceptions during the LLM run
            except Exception as e:
                # Detect a lost connection / VPN drop / endpoint being
                # unreachable. When this happens, EVERY remaining row will
                # fail with the same error, so we must abort the run rather
                # than silently marking all rows as None and writing a
                # "final" output file as if the run succeeded.
                error_msg = str(e).lower()
                fatal_connection_signals = (
                    "public access is disabled",
                    "configure private endpoint",
                    "connection error",
                    "connection aborted",
                    "connection reset",
                    "failed to establish",
                    "max retries exceeded",
                    "name or service not known",
                    "temporary failure in name resolution",
                    "getaddrinfo failed",
                    "nodename nor servname",
                    "403",
                    "cannot unpack non-iterable nonetype object"
                )
                is_fatal_connection = (
                        isinstance(
                            e,
                            (
                                openai.APIConnectionError,
                                openai.APITimeoutError,
                                openai.AuthenticationError,
                                openai.PermissionDeniedError,
                            ),
                        )
                        or any(
                    sig in error_msg for sig in fatal_connection_signals)
                )

                if is_fatal_connection:
                    tqdm.write(
                        f'\n[FATAL] Row {idx}: connection/endpoint failure '
                        f'detected (likely VPN drop):\n{e}\n'
                        f'[FATAL] Aborting run. NO final output will be written. '
                        f'Latest checkpoint is preserved so you can resume '
                        f'once the connection is restored.\n'
                    )
                    logging.error(
                        f'[FATAL] Row: {idx} | Type: CONNECTION_LOST | Error: {e}'
                    )
                    logging.error(
                        '[FATAL] Aborting run without writing final output. '
                        'Resume from the latest checkpoint after reconnecting.'
                    )

                    # Save a checkpoint of progress so far (this row left unprocessed)
                    self._atomic_save_csv(df, checkpoint_path)

                    raise RuntimeError(
                        f'Run aborted at row {idx} due to a connection/endpoint '
                        f'failure (likely VPN drop). Final output was NOT written. '
                        f'Resume from checkpoint: {checkpoint_path}'
                    ) from e

                df.at[idx, 'generation'] = None

                # Print out the error
                tqdm.write(f'Row {idx} Error: \n{e}\n')

                # Log the error and error type in the log file
                error_msg = str(e).lower()
                if "content filter" in error_msg:
                    error_type = "CONTENT_FILTER"
                elif "length limit" in error_msg:
                    error_type = "LENGTH_LIMIT"
                elif "rate limit" in error_msg:
                    error_type = "RATE_LIMIT"
                else:
                    error_type = "UNKNOWN_ERROR"

                logging.error(f'[ERROR] Row: {idx} | Type: {error_type} | Error: {e}')

            # Save checkpoints every X rows (user-specified, default=10 rows)
            if (i + 1) % save_every == 0 or i == len(unprocessed_df) - 1:
                self._atomic_save_csv(df, checkpoint_path)

                # now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                duration = (datetime.now() - start_time)
                duration_minutes = duration.total_seconds() / 60

                logging.info(f'[INFO] CHECKPOINT: Saved at row: {i+1}')
                logging.info(f'[INFO] CHECKPOINT: ├─ Duration:  '
                             f'{duration_minutes:.2f} min.')

                # Log costs at time of checkpoint
                logging.info(f'[INFO] CHECKPOINT: └─ Cum. cost: '
                             f'{cost_tracker.nicely_show_cost(as_string=True)}'
                )

                # Uncomment if you want to show the checkpoint saved in console
                #tqdm.write(f'[INFO] {now} Saved checkpoint at row {i+1}')

        # Flatten the output generation data if desired
        if flatten:
            if self.API_TYPE == 'OPENAI':
                # Flatten once at end
                flattened_df = df['generation'].apply(
                    lambda x: self.flatten_data_old(x)
                    if isinstance(x, dict)
                    else pd.Series()
                )
                df = pd.concat([df, flattened_df], axis=1)

            elif self.API_TYPE == 'AZURE':
                def _safe_flatten(x):
                    if pd.isna(x) or x in ("None", "nan"):
                        return pd.Series()
                    try:
                        # Convert stringified JSON back to dict
                        if isinstance(x, str):
                            x = json.loads(x)
                        return self.flatten_data(x)
                    except Exception as e:
                        print(f"Flattening error: {e}")
                        return pd.Series()

                # Flatten once at end
                flattened_df = df["generation"].apply(_safe_flatten)
                new_cols = [c for c in flattened_df.columns if c not in df.columns]
                if new_cols:
                    df = pd.concat([df, flattened_df[new_cols]], axis=1)

        # Save the final LLM output
        self._atomic_save_csv(df, final_output_path)

        # Log the final cost of LLM generation in the log file
        logging.info(f'[SUCCESS] Final cost:            '
                     f'{cost_tracker.nicely_show_cost(as_string=True)}'
        )

        # Display the completion time and print message
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        end_time = datetime.now()
        duration = (end_time - start_time)
        duration_minutes = duration.total_seconds() / 60
        print(f'\n[SUCCESS] LLM generation run completed ({now} '
              f'| Duration: {duration_minutes:.2f} min.)')
        print(f'[SUCCESS] Final LLM output saved: {final_output_path}')
        logging.info(f'[SUCCESS] LLM generation run completed '
                     f'(Duration: {duration_minutes:.2f} min.)')
        logging.info(f'[SUCCESS] Final LLM output saved: {final_output_path}')

        # Get rid of old checkpoints
        if not keep_checkpoints:
            for f in glob.glob(os.path.join(
                    output_dir, f'checkpoint_{self.model_name}*.csv')
            ):
                try:
                    os.remove(f)
                    print(f'[CLEANUP] Deleted checkpoint(s): {f}')
                    logging.info(f'[CLEANUP] Deleted checkpoint: {f}')
                except Exception as e:
                    print(f'[WARNING] Could not delete checkpoint: {f}: {e}')
        else:
            print(f'[INFO] Keeping all checkpoints in {output_dir}')
            logging.info(f'[INFO] Keeping all checkpoints in {output_dir}')

        return df
