"""
------------------------------------------------------------------------------
Author:         Justin Vinh
Collaborators:  Thomas Sounack
Parent Package: Project Ryland
Creation Date:  2025.10.13

Purpose:
Set up meta info for each model, including cost and API type
------------------------------------------------------------------------------
"""

# ============================================================================
# LAST UPDATED: 2025.01.29
# ============================================================================

# Cost metadata for each model
llm_model_meta = {
    'gpt-4o-2024-05-13-api': {
        'cost_per_1M_token_input':  5.00,
        'cost_per_1M_token_output': 15.00,
        'type':                     'GPT4DFCI'
    },
    'gpt-4o-2024-08-06': {
        'cost_per_1M_token_input':  2.50,
        'cost_per_1M_token_output': 10.00,
        'type':                     'OpenAI'
    },
    'gpt-4o-mini-2024-07-18-api': {
        'cost_per_1M_token_input':  0.15,
        'cost_per_1M_token_output': 0.60,
        'type':                     'GPT4DFCI'
    },
    'gpt-4o': {
        'cost_per_1M_token_input':  2.50,
        'cost_per_1M_token_output': 10.00,
        'type':                     'GPT4DFCI'
    },
    'gpt-5': {
        'cost_per_1M_token_input':  1.25,
        'cost_per_1M_token_output': 10.00,
        'type':                     'GPT4DFCI'
    },
    'gpt-5.2': {
        'cost_per_1M_token_input':  1.75,
        'cost_per_1M_token_output': 14.00,
        'type':                     'GPT4DFCI'
    }
}