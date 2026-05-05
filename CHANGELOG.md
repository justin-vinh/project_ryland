# Project Ryland Changelog
## Author: Justin Vinh
### Lindvall Lab | Dana-Farber Cancer Institute | Contact: justin_vinh@dfci.harvard.edu
##

### v2.9.0 (May 5, 2026)
- added the ability to inject the prompt structure directly into the prompt 
  if the API does not accept pydantic model. This is handled automatically.

### v2.8.0 (May 5, 2026)
- Updated the llm config with the new claude models on databricks
- updated how costs are handled to dynamically handle different units ($, 
  DBU, etc)
- updated the llm_tracker.py function to handle dynamic cost units

### v2.7.0 (May 1, 2026)
- Changed the api_test_key variable to just api_key
- Added the ability for the OpenAI client to also accept a base url if provided

### v2.6.2 (April 16, 2026)
- Updated language in the README to reflect the name change from GPT4DFCI to 
  DFCI AI API


### v2.6.0 (March 25, 2026)
- Added the ability to input a df directly into the process_text function 
  while retaining the ability to also specify an input filepath. An inputted 
  df will take priority over a given filepath.

### v2.5.1 (March 25, 2026)
- Changed the behavior of the dynamic prompt. New dynamic variables must use 
  double curly brackets "{{<var>}}" instead of the depreciated "{<var>}". 
  This was done to avoid accidental matching with prompt text that might 
  use curly brackets.
- Updated API costs

### v2.4.1 (February 25, 2026)
- Fixed a bug with the legacy use of llm_tracker.py

### v2.4.0 (February 23, 2026)
- Changed the default save_every number to 5 (prev. 10)
- Added a new parameter called number_sampled and set the default to 10 (as 
  was previous). Previously, 10 was hard codedd in, but now it can be 
  user-defined
- Changed load_input_file to a static function
- Modified the template notebook to reflect the changes, plus add nicer 
  formatting

### v2.3.0 (February 23, 2026)
- Revised how costs and dates are displayed (and their underlying code)
- Made the log look nicer
- Made the log now track costs and duration at time of each checkpoint
- Updated the llm_tracker.py function to recognize the new log formatting, 
  which has been revised to now include a unique run ID (YYYYMMDD_HHMMSS) 
  and new logic
  - With the new llm_tracker.py change, summarize_llm_runs from 
    llm_generation_utils.py now includes an argument for "legacy=" that will 
    summarize logs with the old formatting

### v2.2.0 (February 18, 2026)
- Added a new module in llm_utils called llm_tracker.py. This is ported into 
  the existing llm_generation_utils module using a wrapper function
  - The purpose of this function will be to scrape the generated log and 
    export a csv summary of all known runs and metrics like cost, duration, 
    rows ran, output filename, etc

### v2.1.10 (February 10, 2026)
- Added more detailed documentation to the README
  - A dictionary of arguments for process_text_data function
  - Instructions for how to use the prompt gallery
  - Notes on the contents of the quickstart
- Fixed various bugs

### v2.1.0 (January 29, 2026)
- Added detailed documentation to the README
- Created a new templates folder that functions as a quickstart function
- Created the new quickstart.py and cli.py files to allow installinng this 
  quickstart template folder to the specified directory.

### v2.0.7 (January 28, 2026)
- bug fixes, user enhancements

### v2.0.0 (January 28, 2026)
- This is a big one. The package is officially on PyPI (technically as of v1.
  3.11), but this is the version that will initally be publicized.
- File tree cleaned to be more user-friendly and files not ready to be 
  published were removed.
  - This necessitated changing the logic of several functions in the 
    llm_generation_utils so that prompts and prompt structures could still 
    be specified (previously hardcoded)
- Added a feature where the user could use their own prompt library using 
  the existing feature or input their prompt directly as an argument.
- Added feature to show the version number for users to ensure they are 
  using the most up-to-date version.

### v1.3.11 (January 28, 2026)
- Changed the sample number for sample_mode to 10
- Added a publish.yml file to prepare the package for publishing on  PyPI
- Added the ability to directl yspecify the API Key values in the LLM wrapper
- Published preliminary version to PyPI
- Fixed various bugs

### v1.3.0 (November 24, 2025)
- llm_generation_utils.py
  - Changed the chat_completion_response section to reflect a change to the 
    Azure API. This change also allows use of gpt-5.
  - The chat completion response parameter set is now dynamically created to 
    reflect whether the use wants to the use the Azure or OpenAI APIs, which 
    use different codes. Part of this dynamic creation is the addition of a 
    temperature parameter for any inputted model that is not gpt-5.
    - This will likely have to be slightly changed in the future when we 
      move beyond gpt-5 since it seems future models will not have temp either
  - Added a new flatten function and implementation code since the new Azure 
    API outputs its generations differently as well. The original flatten 
    function is now called "flatten_data_old" - this will be only used with 
    the OpenAI API until officially depreciated. I have included a gate 
    based on API_TYPE to either use and implement the code from one function 
    or another.
- prompt_structs
  - Added a new class AssessSymptoms (and its helper AssessSymptomsDetails)
    - this struct will change dynamically based on what symptoms are passed 
      to it. I've hard-coded in this particular structure to pull the 
      symptoms from the keyword_mappings module in the data_utils - this way,
      both the prompt and the structure are pulling from the same list of 
      symptoms to assess

### v1.2.4 (October 22, 2025)
- io_utils
  - changed the json loader from the json package to orjson for improved speed


### v1.2.4 (October 22, 2025)
- llm_generation_utils.py
  - made the log file prettier
  - walked back a decision to remove all NA rows under "HYBRID_DEATH_DT" as 
    this would influence downstream stats


### v1.2.3 (October 13, 2025)
- llm_generation_utils.py (formerly llm_utils)
  - added a new class to track cumulative costs from a run
  - added a new llm_config.py file to centralize costs of LLM models. The 
    new cost tracking class pulls data from this file
  - also updated the logging feature to now also output to file
    - of note, this log file does not erase between runs so be aware that 
      existing log files will log ALL runs
  - Revised the progress bar to now include the cost tracker
  - Changed all outputs using the logging module to now go straight to the 
    llm_tracking.log file
  - changed debug_mode to sample_mode for clarity since it is used to return 
    df.head(100)
- cleaned up code and eased technical debt across modules

### v1.2.2 (October 10, 2025)
- llm_utils.py
  - Thomas fixed a bug in the Azure environement that prevented proper 
    functioning of the API in which the output was being casted as an 
    integer when it should have been an "object"
  - Added a new functionality to the LLM_wrapper class and overall module to 
    auto-detect the type of environment (standard OpenAI vs Azure) based on 
    the variables given in the .env file. This way, the same llm utilities 
    could be used for both sensitive and non-sensitive data without total 
    reliance on DFCI's GPT4DFCI


### v1.2.1 (October 8, 2025)
- Added a function (retrieve_llm_prompt_with_inserted_variables) to 
  llm_utils that enable template prompts to be used via placeholder 
  variables that the user can then fill in at time of run. This will be 
  essential to the GWAS project
- Cleaned up the code in the analysis_utils to be more human-readable
- BUG FIXES
  - fixed an error in which all diagnoses that came from the 
    filter_progress_notes function resulted in NA for diagnoses for all 
    notes related to treatment time. Turns out that the error was that the 
    diagnosis df was not merged into the resulting df, which led to NA being 
    added when the notes/treatment df was merged with the notes/diagnosis df 
    at the end of filter_progress_notes

### v1.2.0 (Oct 6, 2025)
- split the ryland_utils into data and llm subpackages
- created a config_llm_prompts.yaml file to act as the central tracker of 
  prompts and provide a reliable way to find past prompts
  - this will be the ideal way to referance various prompts while 
    maintaining metadata and easily accessible txt files to edit
- created the llm_utils module
  - this module ports in a modified version of Thomas Sounack's OpenAI call 
    code
  - Adds in a few improvementst like caching all checkpoints and then 
    autodeleting them at the end
  - also added a new feature to mark output files by gpt model and date of run

### v1.1.1 (Oct 6, 2025)
- Cleaned up the code for analysis_utils.py to
  - have better logic and flow in the code
  - more informative varible names
- Cleaned up the Jupyter noteboks being used to process the data and import 
  the ryland utils

### v1.1.0 (Sep 30, 2025)
- Created analysis_utils.py
  - this function is a heavily modified port of code found in the old NANO 
    progress note prep file as well as various nano_utils cleaning functions.
    - Note that this is not a 1:1 port as the flow of data prep differs from 
      the original code. Code has also been greatly modularized to take 
      advantage of helper functions

### v1.0.0 (Sep 29, 2025)
- Created the Project Ryland utils package
  - Once the Project Ryland (Research sYstem for LLM-based Analytics of Novel 
    Data) package matures through the development of the NANO Gen2 code, it 
    will be separated into its own repo to provide a single source of truth 
    for analytical and cleaning functions related to our LLM research.
  - Refactored ZT's old code and made significant changes in 
    rebuilding it from the ground up
  - extract_text is now split into one main function with 4 helper functions
    - code logic for the extract_text functionality is greatly simplified 
      and made more readable both in code formatting and in comments
    - the output of extract_text is now a list of dicts, and not a list of 
      tuples, which enhances the manipulability of the output data
    - Improved text cleaning
    - Changed the start_keyword key to SECTION
    - sped up the compiling of the mappings by removing them from the loop 
      and putting them in a separate function
  - Created a new keyword_mappings modules to contain distinct keyword lists 
    for use in text extraction and matching. This provides one single 
    source of truth for future mappings
  - Created a io_utils module that now contains the load_onc_drs_json_to_df 
    function and associated helpers