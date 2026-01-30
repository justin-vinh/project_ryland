"""
------------------------------------------------------------------------------
Author:         Justin Vinh
Collaborators:  Thomas Sounack
Parent Package  Project Ryland
Created:        2025.10.10

LLM Prompt Structures File
Purpose: Provides output structures to various prompts
------------------------------------------------------------------------------
"""


from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, create_model

# Basic prompt structure for Example Prompt 1
# ----------------------------------------------------------------------------
class AssessCancerDiagnosis(BaseModel):
    """
    Structured schema for extracting cancer diagnosis from clinical notes
    """
    diagnosis: Optional[str] = Field(
        None,
        description=(
            "Primary cancer diagnosis explicitly stated in the note "
            "(e.g., 'breast cancer', 'glioblastoma', 'small cell lung cancer'). "
            "Return None if no cancer diagnosis is mentioned."
        )
    )
    supporting_text: Optional[str] = Field(
        None,
        description=(
            "Exact span of text from the report that supports the diagnosis."
        )
    )

# Basic Prompt for hard-coded values to return for Example Prompt 2
# ----------------------------------------------------------------------------

# Sets up what structure to return
class LabResult(BaseModel):
    value: Optional[str] = Field(
        None,
        description="Numerical lab value exactly as written in the note"
    )
    text: Optional[str] = Field(
        None,
        description="Exact text span supporting the lab value"
    )

# Sets up what to return the above structure for
class AssessLabs(BaseModel):
    WBC: LabResult
    HCT: LabResult







# Optional: example of what a numerical output structure would look like
class score_scale(int, Enum):
    score_1 = 1
    score_2 = 2
    score_3 = 3

class AssessScore(BaseModel):
    Pain: Optional[score_scale]
    Strength: Optional[score_scale]
    Ataxia: Optional[score_scale]


# Prompt Structure for Example Prompt 2 with Variables
# ----------------------------------------------------------------------------
from itertools import chain
# Import the needed user variables
from project_ryland.templates.standard_quickstart.llm_prompt_gallery.keyword_mappings import (
    example_2_prompt_variables)
all_values = list(chain.from_iterable(example_2_prompt_variables.values()))

class AssessNoteDetail(BaseModel):
    """
    Structured schema for extracting symptom info from progress notes
    """
    status: str = Field(
        None,
        description="The status of the desired vital, demographics, or lab test. "
                    "Should be a numerical value if a lab test or vital. "
                    "If a demographic value, it should be a string"
    )
    text: str = Field(
        None,
        description="Exact text span from the note text that supports the "
                    "assigned status for the lab test, demographic, or vitals."
    )

fields = {
    var: AssessNoteDetail
    for var in all_values
}
AssessNoteValues = create_model(
    'AssessNote',
    **fields
)

# ----------------------------------------------------------------------------