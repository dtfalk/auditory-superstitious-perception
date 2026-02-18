# Analysis module for auditory superstitious perception experiment

from .scoring import (
    score_questionnaire,
    score_all_subjects,
    get_scoring_preset,
    TELLEGEN_SCORING,
    VHQ_SCORING,
    LAUNAY_SLADE_SCORING,
    BAIS_SCORING,
    DES_SCORING,
    FLOW_STATE_SCORING,
)

from .data_verification import (
    verify_subject,
    verify_all_subjects,
    generate_verification_report,
    EXPECTED_QUESTIONS,
    EXPECTED_TRIALS_PER_BLOCK,
    MIN_RT_MS,
    MAX_RT_MS,
    BIAS_THRESHOLD_PERCENT,
)

from .individual_analysis import (
    analyze_subject,
    save_subject_report,
)

from .global_analysis import (
    analyze_all_subjects,
    generate_global_report,
    export_to_csv,
)

__all__ = [
    # Scoring
    'score_questionnaire',
    'score_all_subjects', 
    'get_scoring_preset',
    'TELLEGEN_SCORING',
    'VHQ_SCORING',
    'LAUNAY_SLADE_SCORING',
    'BAIS_SCORING',
    'DES_SCORING',
    'FLOW_STATE_SCORING',
    # Verification
    'verify_subject',
    'verify_all_subjects',
    'generate_verification_report',
    'EXPECTED_QUESTIONS',
    'EXPECTED_TRIALS_PER_BLOCK',
    'MIN_RT_MS',
    'MAX_RT_MS',
    'BIAS_THRESHOLD_PERCENT',
    # Individual
    'analyze_subject',
    'save_subject_report',
    # Global
    'analyze_all_subjects',
    'generate_global_report',
    'export_to_csv',
]
