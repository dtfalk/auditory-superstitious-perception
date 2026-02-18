"""
Questionnaire Scoring Module
============================
General scoring functions for questionnaires with support for:
- Custom value mappings per question
- Reverse scoring
- Subscale calculations
"""

import csv
import os
from typing import Callable


def score_questionnaire(
    filepath: str,
    scoring_scheme: dict | None = None,
    reverse_items: list[int] | None = None,
    max_value: int | None = None,
    subscales: dict[str, list[int]] | None = None,
) -> dict:
    """
    Score a questionnaire CSV file.
    
    Args:
        filepath: Path to the questionnaire CSV file
        scoring_scheme: Dict mapping response text to numeric value.
                       If None, assumes responses are already numeric.
                       Example: {'Never': 0, 'Rarely': 1, 'Often': 2, 'Always': 3}
        reverse_items: List of 1-indexed question numbers that should be reverse scored.
                      Example: [2, 5, 8] means Q2, Q5, Q8 are reverse scored.
        max_value: Maximum value on the scale (required if reverse_items is provided).
                  For reverse scoring: new_value = max_value - original_value
        subscales: Dict mapping subscale names to lists of 1-indexed question numbers.
                  Example: {'absorption': [1, 2, 3], 'dissociation': [4, 5, 6]}
    
    Returns:
        Dict with:
            - 'subject_number': Subject ID
            - 'raw_responses': List of raw response values
            - 'scored_responses': List of scored (possibly reversed) values 
            - 'total_score': Sum of all scored values
            - 'mean_score': Mean of all scored values
            - 'subscales': Dict of subscale scores (if subscales provided)
            - 'num_questions': Number of questions
            - 'num_answered': Number of questions with valid responses
            - 'missing_questions': List of question indices with missing data
    """
    if not os.path.exists(filepath):
        return {'error': f'File not found: {filepath}'}
    
    with open(filepath, 'r', newline='') as f:
        reader = csv.reader(f)
        lines = list(reader)
    
    if len(lines) < 2:
        return {'error': 'File has no data rows'}
    
    header = lines[0]
    # First row after header is numeric values, second is text labels
    data_row = lines[1]
    
    subject_number = data_row[0]
    raw_responses = data_row[1:]  # Skip subject number column
    num_questions = len(raw_responses)
    
    # Convert to numeric
    scored_responses = []
    missing_questions = []
    
    for i, response in enumerate(raw_responses):
        q_num = i + 1  # 1-indexed
        
        # Handle empty or missing responses
        if response == '' or response is None:
            scored_responses.append(None)
            missing_questions.append(q_num)
            continue
        
        # Apply scoring scheme if provided
        if scoring_scheme is not None:
            if response in scoring_scheme:
                value = scoring_scheme[response]
            else:
                # Try to extract numeric part
                try:
                    value = int(''.join(c for c in response if c.isdigit()))
                except ValueError:
                    scored_responses.append(None)
                    missing_questions.append(q_num)
                    continue
        else:
            try:
                value = int(response) if response.isdigit() else float(response)
            except ValueError:
                # Try to extract leading number
                try:
                    value = int(''.join(c for c in response if c.isdigit()))
                except ValueError:
                    scored_responses.append(None)
                    missing_questions.append(q_num)
                    continue
        
        # Apply reverse scoring
        if reverse_items and q_num in reverse_items:
            if max_value is None:
                raise ValueError("max_value required when reverse_items is provided")
            value = max_value - value
        
        scored_responses.append(value)
    
    # Calculate totals
    valid_scores = [s for s in scored_responses if s is not None]
    total_score = sum(valid_scores) if valid_scores else 0
    mean_score = total_score / len(valid_scores) if valid_scores else 0
    
    result = {
        'subject_number': subject_number,
        'raw_responses': raw_responses,
        'scored_responses': scored_responses,
        'total_score': total_score,
        'mean_score': round(mean_score, 3),
        'num_questions': num_questions,
        'num_answered': len(valid_scores),
        'missing_questions': missing_questions,
    }
    
    # Calculate subscales
    if subscales:
        subscale_scores = {}
        for name, items in subscales.items():
            subscale_values = []
            for q_num in items:
                idx = q_num - 1  # Convert to 0-indexed
                if idx < len(scored_responses) and scored_responses[idx] is not None:
                    subscale_values.append(scored_responses[idx])
            
            subscale_scores[name] = {
                'total': sum(subscale_values) if subscale_values else 0,
                'mean': round(sum(subscale_values) / len(subscale_values), 3) if subscale_values else 0,
                'num_items': len(items),
                'num_answered': len(subscale_values),
            }
        result['subscales'] = subscale_scores
    
    return result


def score_all_subjects(
    results_dir: str,
    questionnaire_name: str,
    scoring_scheme: dict | None = None,
    reverse_items: list[int] | None = None,
    max_value: int | None = None,
    subscales: dict[str, list[int]] | None = None,
) -> list[dict]:
    """
    Score a questionnaire for all subjects in the results directory.
    
    Args:
        results_dir: Path to the results directory containing subject folders
        questionnaire_name: Name of the questionnaire file (without subject number)
                           Example: 'tellegen' will look for 'tellegen_{subject}.csv'
        (other args same as score_questionnaire)
    
    Returns:
        List of score dicts for each subject
    """
    all_scores = []
    
    for subject_folder in os.listdir(results_dir):
        subject_path = os.path.join(results_dir, subject_folder)
        if not os.path.isdir(subject_path):
            continue
        
        # Skip non-numeric folder names (like analysis)
        if not subject_folder.isdigit():
            continue
        
        filepath = os.path.join(subject_path, f'{questionnaire_name}_{subject_folder}.csv')
        if os.path.exists(filepath):
            scores = score_questionnaire(
                filepath,
                scoring_scheme=scoring_scheme,
                reverse_items=reverse_items,
                max_value=max_value,
                subscales=subscales,
            )
            all_scores.append(scores)
    
    return all_scores


# =============================================================================
# PREDEFINED SCORING SCHEMES
# =============================================================================

TELLEGEN_SCORING = {
    'scoring_scheme': None,  # Already numeric (0-3)
    'reverse_items': None,
    'max_value': 3,
}

VHQ_SCORING = {
    'scoring_scheme': {'No': 0, 'Yes': 1},
    'reverse_items': None,
    'max_value': 1,
}

LAUNAY_SLADE_SCORING = {
    'scoring_scheme': None,  # 0-4 Likert
    'reverse_items': None,
    'max_value': 4,
}

BAIS_SCORING = {
    'scoring_scheme': None,  # 1-7 scale
    'reverse_items': None,
    'max_value': 7,
}

DES_SCORING = {
    'scoring_scheme': None,  # 0-100 scale
    'reverse_items': None,
    'max_value': 100,
}

FLOW_STATE_SCORING = {
    'scoring_scheme': None,  # 1-5 scale
    'reverse_items': None,
    'max_value': 5,
}


def get_scoring_preset(questionnaire_name: str) -> dict:
    """Get predefined scoring parameters for known questionnaires."""
    presets = {
        'tellegen': TELLEGEN_SCORING,
        'vhq': VHQ_SCORING,
        'launay_slade': LAUNAY_SLADE_SCORING,
        'bais_c': BAIS_SCORING,
        'bais_v': BAIS_SCORING,
        'dissociative_experiences': DES_SCORING,
        'flow_state_scale': FLOW_STATE_SCORING,
    }
    return presets.get(questionnaire_name, {})


if __name__ == '__main__':
    # Example usage
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
    
    # Score Tellegen for all subjects
    scores = score_all_subjects(results_dir, 'tellegen', **TELLEGEN_SCORING)
    for s in scores:
        print(f"Subject {s['subject_number']}: Total={s['total_score']}, Mean={s['mean_score']}")
