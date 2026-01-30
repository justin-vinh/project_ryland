# project_ryland

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

## Description
This project develops standardized tools to use LLMs in research studies for 
improving patient care. The two main features are:
1) Enable a user-firendly access point for the use of GPT4DFCI, especially 
   for those without a computing background
2) (In development) Offer a set of tools to process OncDRS data and prepare 
   it for use in LLM research 

### History
This project was conceived in fall 2025 when Justin Vinh noticed that no 
modular, user-friendly package existed at the Dana-Farber Cancer Institute in 
Boston, MA, to allow users to take advantage of the newly offered GPT4DFCI. 
GPT4DFCI is the HIPAA-compliant large language model (LLM) interface offered 
to researchers, and the associated API can be powerful if utilized. So he 
developed this project in collaboration with Thomas Sounack and the support 
of the Lindvall Lab to fill this gap.

RYLAND 
stands for **"Research sYstem for LLM-based Analytics of Novel Data."** 
Ryland is the protagonist of Justin's favorite book Project Hail Mary by 
Andy Weir.

### Project Organization

```
project_ryland/
├── .github/
│   └── workflows/
│       └── publish.yml
├── .gitignore
├── CHANGELOG.md
├── LICENSE
├── project_ryland/
│   ├── __init__.py
│   └── llm_utils/
│       ├── __init__.py
│       ├── llm_config.py
│       └── llm_generation_utils.py
├── pyproject.toml
└── README.md
```
### Features of the LLM Utililties Package
1) Enables a user-friendly use of the GPT4DFCI API
2) Enables the use of a prompt library to keep track of prompts and 
   associated metadata

## Instructions for Use
Note: A copy-paste version of the script is available at the end. Variable 
definitions can also be found at the end after the example script.

1. Import llm_generation_utils from Project Ryland
```
from project_ryland.llm_utils import llm_generation_utils as llm
```
2. In your Jupyter notebook or python script, define your ```endpoint``` and
   ```entra_scope```. The endpoint is user-specific, while the entra_scope 
   is the same for all users (current default for DFCI shown below). These 
   values should have been provided when you were granted DFCI API access.
3. Specify the LLM model that you will be using to run your prompts.
    - Model names can be found in the [llm_config.py file](https://github.com/justin-vinh/project_ryland/blob/main/project_ryland/llm_utils/llm_config.py).

```
ENDPOINT = "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ENTRA_SCOPE = "https://cognitiveservices.azure.com/.default"
model_name="gpt-5"
```

4. Run the LLM_wrapper function to initialize the API.
    - Note that this only has to be done once per run. You can call the API 
      multiple times in one run 

```
LLM_wrapper = llm.LLM_wrapper(
    model_name,
    endpoint=ENDPOINT,
    entra_scope=ENTRA_SCOPE,
)
```



3. Declare the path to your input CSV file. 
4. Declare the path to your LLM Prompt Library if you will be utilizing that 
   feature. A [template prompt gallery]() is available for download from the 
   GitHub. Add the library to the same directory as your main script. Use of 
   the gallery is highly recommended to track prompts texts, prompt 
   structures, and associated metadata.

```

input_file = 'pathology_llm_tests.csv'
gallery_path = "llm_prompt_gallery"
```
[llm_prompt_gallery](../rheelab_commons/rheelab_commons/project_ryland/llm_utils/llm_prompt_gallery)
```
dfp_new = LLM_wrapper.process_text_data(
    # Essential to specify
    input_file_path=input_file,
    text_column="SECTION_TEXT",
    format_class=ps.AssessNanoPathology,
    use_prompt_gallery=False,

    # Specify if using the prompt gallery, else put None
    prompt_gallery_path=gallery_path,
    prompt_to_get="gwas_symptoms_prompt_v1",
    user_prompt_vars=gwas_prompt_variables_v1,

    # Specify if NOT using the prompt gallery, else put None
    prompt_text = "Give me a hello",

    # Optional to specify
    output_dir="output_tests",
    flatten=True,
    sample_mode=False,
    resume=True,
    keep_checkpoints=False,
    save_every=10,
```







--------

