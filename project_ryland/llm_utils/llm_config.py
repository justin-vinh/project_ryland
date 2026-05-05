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
# LAST UPDATED: 2025.03.25
# ============================================================================

# Cost metadata for each model
llm_model_meta = {

    # GPT MODELS (AZURE)
    'gpt-4o-2024-05-13-api': {
        'cost_per_1M_token_input':  5.00,
        'cost_per_1M_token_output': 15.00,
        'cost_unit':                '$',
        'type':                     'GPT4DFCI',
        'last_updated':             '2026-05-01'
    },
    'gpt-4o-2024-08-06': {
        'cost_per_1M_token_input':  2.50,
        'cost_per_1M_token_output': 10.00,
        'cost_unit':                '$',
        'type':                     'OpenAI',
        'last_updated':             '2026-05-01'
    },
    'gpt-4o-mini-2024-07-18-api': {
        'cost_per_1M_token_input':  0.15,
        'cost_per_1M_token_output': 0.60,
        'cost_unit':                '$',
        'type':                     'GPT4DFCI',
        'last_updated':             '2026-05-01'
    },
    'gpt-4o': {
        'cost_per_1M_token_input':  2.50,
        'cost_per_1M_token_output': 10.00,
        'type':                     'GPT4DFCI',
        'last_updated':             '2026-05-01'
    },
    'gpt-5': {
        'cost_per_1M_token_input':  1.25,
        'cost_per_1M_token_output': 10.00,
        'cost_unit':                '$',
        'type':                     'GPT4DFCI',
        'last_updated':             '2026-05-01'
    },
    'gpt-5.2': {
        'cost_per_1M_token_input':  1.75,
        'cost_per_1M_token_output': 14.00,
        'cost_unit':                '$',
        'type':                     'GPT4DFCI',
        'last_updated':             '2026-05-01'
    },
    'gpt-5.4': {
        'cost_per_1M_token_input':  2.50,
        'cost_per_1M_token_output': 15.00,
        'cost_unit':                '$',
        'type':                     'GPT4DFCI',
        'pricing_type':             'short context',
        'last_updated':             '2026-05-01'
    },

    # CLAUDE MODELS (DATABRICKS)
    'databricks-claude-sonnet-4-6': {
        'cost_per_1M_token_input':  42.857,
        'cost_per_1M_token_output': 214.286,
        'cost_unit':                'DBU',
        'type':                     'Claude',
        'pricing_type':             'NA',
        'last_updated':             '2026-05-01'
    },
    'databricks-claude-opus-4-7': {
        'cost_per_1M_token_input':  71.429,
        'cost_per_1M_token_output': 357.143,
        'cost_unit':                'DBU',
        'type':                     'Claude',
        'pricing_type':             'NA',
        'last_updated':             '2026-05-01'
    },

}