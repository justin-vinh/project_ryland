# Project Ryland

## Description
This project enables users to more easily access and use the GPT4DFCI API.

### Features
- **User-friendly interface** for using the GPT4DFCI API
- **Local cost tracking** for live estimates of running costs
- **Automatic logs** to keep track of prompts, model used, and costs
- **A visual progress bar** to estimate time until completion
- **Automatic checkpointing** of operations to enable resuming if interrupted
- **A prompt gallery** to help users keep track of prompts and add metadata
- **Input of user-created prompts** for quick plug-and-play usage

The package is still in development and more features will be added with time.

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
│   ├── cli.py
│   ├── llm_utils/
│   │   ├── __init__.py
│   │   ├── llm_config.py
│   │   └── llm_generation_utils.py
│   └── templates/
│       ├── __init__.py
│       ├── quickstart.py
│       └── standard_quickstart/
│           ├── __init__.py
│           ├── llm_prompt_gallery/
│           │   ├── __init__.py
│           │   ├── config_llm_prompts.yaml
│           │   ├── example_prompt_1.txt
│           │   ├── example_prompt_2_with_variables.txt
│           │   ├── example_prompt_2.txt
│           │   ├── keyword_mappings.py
│           │   └── prompt_structs.py
│           ├── project_ryland_quickstart.ipynb
│           └── synthetic_clinical_notes.csv
├── pyproject.toml
└── README.md

```
---

## Instructions for General Use


### Installing the GPT4DFCI API
1. Ensure that you are on the DFCI network or running the VPN client.
2. Follow the instructions on the [Azure website](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest) to install the Azure CLI 
   tool. This will be necessary to enable the API for GPT4DFCI.
2. Once installed, run this command in Terminal (MacOS) or Command Prompt 
   (Windows):
```
az login --allow-no-subscriptions
```
3. Running the prior command will open a window for you to login into your 
   account. Log in.

### Installing Project Ryland
1. You can install Project Ryland using pip:
```bash
pip install project-ryland
```

### Using Project Ryland (Quickstart)
**Note: You must be using the VPN Client or be on the DFIC network to use 
GPT4DFCI.**
1. Use the quickstart to get off the ground quickly! To create the 
   quickstart in your working directory, run this command from a 
   python script:
```
from project_ryland.templates.quickstart import create_quickstart
create_quickstart(dest="~/quickstart")
```
or use the command line tool:
```bash
project-ryland-init quickstart
```
The quickstart contains a template prompt gallery (`config_llm_prompts.yaml`)
, two static prompts (`example_prompt_1.txt` and `example_prompt_2.txt`), one 
dynamic prompt (`example_prompt_2_with_variables.txt`), and their associated 
prompt structures (`prompt_structs.py`). The `keyword_mappings.py` file 
contains example user variables to be used with the dynamic prompt. Finally, 
`synthetic_clinical_notes.csv` contains generated clinical data for quick 
demonstration use of the prompts. See below for instructions for how to use 
the prompt gallery.

The `project_ryland_quickstart.ipynb` file contains the general code to run 
Project Ryland.
```
standard_quickstart/
├── __init__.py
├── llm_prompt_gallery/
│   ├── __init__.py
│   ├── config_llm_prompts.yaml
│   ├── example_prompt_1.txt
│   ├── example_prompt_2_with_variables.txt
│   ├── example_prompt_2.txt
│   ├── keyword_mappings.py
│   └── prompt_structs.py
├── project_ryland_quickstart.ipynb
└── synthetic_clinical_notes.csv
```


### Using Project Ryland (Manual)
Note: A copy-paste version of the script is available at the end. Variable 
definitions can also be found at the end after the example script.

**Note: You must be using the VPN Client or be on the DFIC network to use 
GPT4DFCI.**

1. If this is your first time using Project Ryland, you must install it into 
   your environment. In Terminal or Command Prompt run the following 

2. Import llm_generation_utils from Project Ryland
```
from project_ryland.llm_utils import llm_generation_utils as llm
```
3. In your Jupyter notebook or python script, define your ```endpoint``` and
   ```entra_scope```. The endpoint is user-specific, while the entra_scope 
   is the same for all users (current default for DFCI shown below). These 
   values should have been provided when you were granted GPT4DFCI API access.
4. Specify the LLM model that you will be using to run your prompts.
    - Model names can be found in the [llm_config.py file](https://github.com/justin-vinh/project_ryland/blob/main/project_ryland/llm_utils/llm_config.py).

```
ENDPOINT = "https://xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
ENTRA_SCOPE = "https://cognitiveservices.azure.com/.default"
model_name = "gpt-5"
```

5. Run the LLM_wrapper function to initialize the API.
    - Note that this only has to be done once per run. You can call the API 
      multiple times in one run 

```
LLM_wrapper = llm.LLM_wrapper(
    model_name,
    endpoint=ENDPOINT,
    entra_scope=ENTRA_SCOPE,
)
```
6. Declare the path to your input CSV file. 
7. Declare the path to your LLM Prompt Gallery if you will be utilizing that 
   feature. A [template prompt gallery]() is available for download from the 
   GitHub. Add the prompt gallery to the same directory as your main script. 
   Use of 
   the gallery is highly recommended to track prompts texts, prompt 
   structures, and associated metadata.

```
input_file = 'pathology_llm_tests.csv'
gallery_path = "llm_prompt_gallery"
```
8. Use the generation to obtain your LLM output.
```
df = LLM_wrapper.process_text_data(
    # Essential to specify
    input_file_path=input_file,
    text_column=text_column,
    format_class=prompt_struct,
    use_prompt_gallery=use_prompt_gallery,

    # Specify if using the prompt gallery, else put None
    prompt_gallery_path=gallery_path,
    prompt_to_get=gallery_prompt,
    user_prompt_vars=user_vars,

    # Specify if NOT using the prompt gallery, else put None
    prompt_text=prompt_text,

    # Optional to specify
    output_dir=output_directory,
    flatten=True,
    sample_mode=sample_mode,
    resume=True,
    keep_checkpoints=False,
    save_every=10,
)
```
---

## Instructions for Using the Prompt Gallery
The prompt gallery was designed by Justin as a method of storing prompt 
metadata and is made to facilitate iterative prompt design. This metadata is 
stored in the YAML file shown in the quickstart. Several prompts are already 
detailed in the template and can be a good place to start. Let's look at one 
of them:
```
example_1_prompt:
  filename: example_prompt_1.txt
  description: |
    Determine of what type of cancer the patient has based on the 
    note content.
  author: Sidney Farber
  date: 2025.10.06
```
- The first key `example_1_prompt` is the name of the prompt and is used in 
  the API call. The prompt name does _not_ need to be the same as the prompt 
  filename.
- `filename` specifies the path to the prompt txt file, relative to the 
  gallery directory. In this case, the txt file is in the same directory as 
  the prompt gallery YAML file and so only the prompt filename is needed.
- The other metadata keys like `description`, `author`, and `date` are 
  optional and can be changed to any kind of other metadata suiting the 
  user's needs. A vertical line `|` allows the user to add a multiline 
  value (as in the case of `description`).

---
## Dictionary

### Arguments for process_text_data function

#### Necessary Arguments at All Times
- `input_file_path` specifies the path to your input CSV file (only CSV 
  files are currently accepted).
- `text_column` specifies the column within the CSV file that serves as the 
  input to the LLM.
- `format_class` specifies the class structure that enforces the desired 
  promopt output.
- `use_prompt_gallery` is a boolean (True/False) input that directs the 
  function to use the prompt gallery if set to True. Note that setting 
  this argument to True will override anything specified by the 
  `prompt_text` argument.

#### Necessary Arguments _if_ Using Prompt Gallery
- `prompt_gallery_path` specifies the path to the prompt gallery.
- `prompt_to_get` specifies the prompt name as listed in the prompt gallery.
- `user_prompt_vars` specifies the dictionary that contains the key-value 
  pairs between the placeholder variables and the desired user-specified 
  variables to be inputted. See the quickstart example for how this should 
  be done.

#### Necessary Arguments _if_ Using a User Prompt
- `prompt_text` specifies a string that serves as a user-inputted prompt. 
  Use this argument only if the prompt gallery is not being used.

#### Optional Arguments
- `output_dir` specifies the path to the output directory. If the 
  inputted directory does not exist, it will be generated. If not specified, 
  the default output location will be the same as the main script.
- `flatten` is a boolean (True/False) that specifies whether to turn the 
  output dictionary into individual columns. Default: True
- `sample_mode` is a boolean (True/False) that specifies whether to only 
  process the first 10 rows of the input CSV (sampling the data). It is 
  recommended to use sample_mode when first running new data, prompts, or 
  prompt structures to verify that the intended output is correct. Default: 
  False.
- `resume` is a boolean (True/False) that specifies whether to resume from a 
  checkpoint if generation is interrupted. Default: True.
- `keep_checkpoints` is a boolean (True/False) that specifies whether 
  checkpoints will be auto-deleted after a run. Setting it to true will keep 
  every generated checkpoint after a generation. Default: False.
- `save_every` is an integer that specifies the interval between checkpoints.
  The default is 10 rows.



---
## License
Project Ryland is released under the MIT License. See LICENSE file for more details.

## Support
If you encounter any issues or have questions, please file an issue on the 
GitHub issue tracker. We appreciate suggestions for improvement as well!

## Acknowledgements
Project Ryland was developed with the support of **Thomas Sounack** and the 
**Lindvall Lab**, led by Dr.
Charlotta Lindvall, MD, PhD, at the Dana-Farber Cancer Institute. We thank 
all the contributors for their valuable input and support.

## Citation
If you use **project_ryland** in your research or publications, please cite this repository:

Vinh J, Sounack T. *project_ryland: Research sYstem for LLM-based Analytics of Novel Data*. GitHub. https://github.com/justin-vinh/project_ryland

You can also use the GitHub **“Cite this repository”** button on the right sidebar for
formatted citations (APA, BibTeX, etc.).

### BibTeX

```bibtex
@software{project_ryland,
  author = {Vinh, Justin and Sounack, Thomas},
  title = {project_ryland: Research sYstem for LLM-based Analytics of Novel Data},
  year = {2026},
  url = {https://github.com/justin-vinh/project_ryland}
}
```
--------

