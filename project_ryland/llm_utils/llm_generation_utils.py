"""
------------------------------------------------------------------------------
Author:         Justin Vinh
Collaborators:  Thomas Sounack
Institution:    Dana-Farber Cancer Institute
Working Groups: Lindvall & Rhee Labs
Parent Package: Project Ryland
Creation Date:  2025.10.06
Last Modified:  2025.11.24

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
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import openai
import pandas as pd
import yaml
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from environs import Env
from openai import AzureOpenAI, OpenAI
from pydantic import ValidationError
from tqdm import tqdm

from .llm_config import llm_model_meta
from project_ryland import __version__

# --- Configure logging ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clear existing handlers
logger.handlers = []

# File handler
file_handler = logging.FileHandler("llm_tracking.log")
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(message)s", "%Y-%m-%d %H:%M:%S"
))
logger.addHandler(file_handler)

# Silence noisy libraries
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
# --- Configure logging ---


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
    prompt_vars = re.findall(r'{(.*?)}', text)
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

    def update_cost(self, llm_output_meta):
        """Tracks cumulative costs"""
        # Calculate costs
        input_tokens = llm_output_meta.usage.prompt_tokens
        output_tokens = llm_output_meta.usage.completion_tokens
        input_cost = self.input_1M_token_cost * input_tokens / 1e6
        output_cost = self.output_1M_token_cost * output_tokens / 1e6

        # Update costs
        self.input_cost += input_cost
        self.output_cost += output_cost
        self.total_cost = self.input_cost + self.output_cost

        # Add cumulative costs to a dict, handle special case if costs < $0.01
        tracker_output = {
            'Input': f'${'<0.01' 
                if self.input_cost < 0.01 
                else f'{self.input_cost:.2f}'}',
            'Output': f'${'<0.01' 
                if self.output_cost < 0.01 
                else f'{self.output_cost:.2f}'}',
            'Total': f'${'<0.01' 
                if self.total_cost < 0.01 
                else f'{self.total_cost:.2f}'}'
        }
        # logging.info(tracker_output)  # Uncomment if you want cum. costs per row

        return tracker_output

    def summary(self):
        return {
            'input_cost': self.input_cost,
            'output_cost': self.output_cost,
            'total_cost': self.total_cost,
        }


class LLM_wrapper:
    def __init__(
            self,
            model_name: str,
            endpoint: str = None,
            entra_scope: str = None,
            api_test_key: str = None,
            env_abs_path: str = None):
        """Set up token provider and Azure OpenAI client"""
        # Sets up the environment depending on what was read from the .env file

        if (endpoint is None and
            entra_scope is None and
            api_test_key is None):
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
            api_test_key = env.str("API_TEST_KEY", None)

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
        elif api_test_key:
            # Detected standard OpenAI environment
            print(f'[INFO] Detected standard OpenAI configuration')
            self.API_TYPE = 'OPENAI'
            self.client = OpenAI(api_key=api_test_key)
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
        cost_tracker: LLMCostTracker):
        """Call the Azure OpenAI API with structured response parsing"""

        # Sets up a parameter set for the chat completion response
        # Will add to this set based on API type or model type
        chat_response_params = {
            'model': self.model_name,
            'messages': [{"role": "system", "content": prompt},
                        {"role": "user", "content": input_text}],
        }

        # Sets the temperature to 0 if using any model other than gpt-5
        if 'gpt-5' not in self.model_name:
            chat_response_params['temperature'] = 0.0

        try:
            # Uses the chat response pathway for the new DFCI Azure API
            if self.API_TYPE == 'AZURE':
                chat_response_params['response_format'] = format_class
                completion = self.client.beta.chat.completions.parse(
                    **chat_response_params
                )
                return completion.choices[0].message.parsed, completion

            # Uses the chat response pathway for the public OpenAI API
            elif self.API_TYPE == 'OPENAI':
                schema = [openai.pydantic_function_tool(format_class)]
                schema_clean = self.remove_strict_field(schema)
                function_name = self.extract_name_value(schema_clean)

                chat_response_params['tools'] = schema
                chat_response_params['tool_choice'] = {
                    'type': 'function',
                    'function': {'name': function_name}
                }

                # Allow only 3 retries in calling the API
                for attempt in range(3):
                    completion = self.client.chat.completions.create(
                        **chat_response_params
                    )
                    if completion:
                        response = (completion.choices[0]
                                    .message.tool_calls[0]
                                    .function.arguments)
                        return [json.loads(response), completion]

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
    def load_input_file(self, input_file: str,
                        text_column: str,
                        sample_mode: bool = False) \
            -> pd.DataFrame:
        """Load input CSV file and validate columns"""
        print(f'[INFO] Reading input data from \n{input_file}\n')
        df = pd.read_csv(input_file)

        if text_column not in df.columns:
            raise ValueError(f"Missing required col {text_column} in input file")

        if sample_mode:
            return df.head(10)
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
        input_file_path,
        text_column,
        format_class,
        use_prompt_gallery: bool = False,

        prompt_gallery_path: str = None,
        prompt_to_get: str = None,
        prompt_text: str = None,
        user_prompt_vars = None,

        sample_mode: bool = False,
        flatten: bool = True,
        save_every: int = 10,
        output_dir: str = '../tmp',
        keep_checkpoints: bool = False,
        resume: bool = True
    ):
        """
        Process text data with the LLM and auto-generates unique output filenames.
        """
        # Log start of run
        logging.info(f'[INFO] project_ryland version {__version__}')
        logging.info('[INFO] New LLM generation run starting...')
        logging.info(f'[INFO] Loading data from: {input_file_path}')
        print(f'[INFO] Project Ryland:      v{__version__}')

        # Ensure output dir exists
        os.makedirs(output_dir, exist_ok=True)

        # Generate the timestamped final output and checkpoint names
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        base_prefix = f'{self.model_name}_{timestamp}'
        checkpoint_path = os.path.join(output_dir, f'checkpoint_{base_prefix}.csv')
        final_output_path = os.path.join(output_dir, f'final_{base_prefix}.csv')

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

        logging.info(f'[INFO] Prompt loaded: {prompt_to_get}')

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
            df = self.load_input_file(input_file_path, text_column, sample_mode=sample_mode)
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
        # Sets up the progress bar
        bar = tqdm(unprocessed_df.iterrows(),
                   total=len(unprocessed_df),
                   desc=f'Processing data')

        # Row by row, generate the LLM response to the input data
        for i, (idx, row) in enumerate(bar):
            try:
                input_text = row[text_column]
                response, completion = self.openai_chat_completion_response(
                    prompt,
                    input_text,
                    format_class,
                    cost_tracker)
                # df.at[idx, 'generation'] = response

                if hasattr(response, "model_dump"):  # Pydantic v2
                    df.at[idx, "generation"] = json.dumps(response.model_dump())
                elif hasattr(response, "dict"):  # Pydantic v1
                    df.at[idx, "generation"] = json.dumps(response.dict())
                else:
                    df.at[idx, "generation"] = json.dumps(response)

                # Add the costs to the progress bar
                bar.set_postfix(cost_tracker.update_cost(completion))

            except Exception as e:
                tqdm.write(f'Error with row {idx} → Error: {e}')
                df.at[idx, 'generation'] = None

            # Save checkpoints every X rows (user-specified)
            if (i + 1) % save_every == 0 or i == len(unprocessed_df) - 1:
                with open(checkpoint_path, 'w') as f:
                    df.to_csv(f, index=False)
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logging.info(f'[INFO] Saved checkpoint at row {i+1}')
                # Uncomment if you want to show the checkpoint saved in console
                #tqdm.write(f'[INFO] {now} Saved checkpoint at row {i+1}')

        # Log the final cost of LLM generation in the log file
        logging.info(f'[INFO] Cost: {cost_tracker.update_cost(completion)}')

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
        df.to_csv(final_output_path, index=False)

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
                    logging.info(f'[CLEANUP] Deleted checkpoint: {f}'
                                 f'\n---------------------------------------'
                                 f'----------------------------------------')
                except Exception as e:
                    print(f'[WARNING] Could not delete checkpoint: {f}: {e}')
        else:
            print(f'[INFO] Keeping all checkpoints in {output_dir}')
            logging.info(f'[INFO] Keeping all checkpoints in {output_dir}'
                         f'\n-------------------------------------------'
                         f'----------------------------------------')

        return df
