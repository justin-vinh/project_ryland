# Project Ryland Changelog
## Author: Justin Vinh
### Lindvall & Rhee Labs | Dana-Farber Cancer Institute | Contact: justin_vinh@dfci.harvard.edu
##

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
  variables that the user can then fill in at time of run. This is will be 
  essential to the GWAS project
- Cleaned up the code in the analysis_utils to be more human readable
- BUG FIXES
  - fixed an error in which all diagnoses that came from the 
    filter_progress_notes function resulted in NA for diagnoses for all 
    notes related to treatment time. Turns out that the error was that the 
    diagnosis df was not merged into the resulting df, which led to NA being 
    added when the notes/treatment df was merged with the notes/diagnosis df 
    at the end of filter_progress_notes

### v1.2 (Oct 6, 2025)
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

### v1.1 (Sep 30, 2025)
- Created analysis_utils.py
  - this function is a heavily modified port of code found in the old NANO 
    progress note prep file as well as various nano_utils cleaning functions.
    - Note that this is not a 1:1 port as the flow of data prep differs from 
      the original code. Code has also been greatly modularized to take 
      advantage of helper functions

### v1.0 (Sep 29, 2025)
- Created the Project Ryland utils package
  - Once the Project Ryland (Research sYstem for LLM-based Analytics of Novel 
    Data) package matures through the development of the NANO Gen2 code, it 
    will be separated into its own repo to provide a single source of truth 
    for analytical and cleaning functions related to our LLM research.
  - Refactored Zach Tentor's old code and made significant changes in 
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
- Created the 0.00 data prep EDA file
  - Did some exploratory data analysis of the Lindvall 204475 dataset
  - Terminology is also brought into unison with code processing pathology and progress notes 
    (like calling the extracted text "EXTRACTED_TEXT")
  - the 0.00_processed_imaging_notes.csv file now contains _all_ rows from 
    the original df, unlike Zach's original code, which dropped rows which 
    had NA in the IMPRESSION_TEXT column
