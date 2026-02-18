"""
Data Verification Module
========================
Comprehensive checks for experiment data integrity:
- Questionnaire completion
- Trial data completeness
- Response time analysis
- Bias detection
- Data quality flags
"""

import csv
import os
from datetime import datetime
from typing import Any


# =============================================================================
# CONFIGURATION
# =============================================================================

# Expected number of questions per questionnaire
EXPECTED_QUESTIONS = {
    'tellegen': 34,
    'vhq': 14,
    'launay_slade': 16,
    'bais_c': 14,
    'bais_v': 14,
    'dissociative_experiences': 28,
    'flow_state_scale': 9,
}

# Expected number of trials per block
EXPECTED_TRIALS_PER_BLOCK = {
    'full_sentence': 60,  # Adjust based on actual experiment design
    'imagined_sentence': 60,
}

# Response time thresholds (in nanoseconds for trial timestamps)
MIN_RT_MS = 100  # Faster than this is suspicious
MAX_RT_MS = 30000  # Slower than this might indicate inattention

# Bias thresholds
BIAS_THRESHOLD_PERCENT = 80  # >80% same response = bias flag


# =============================================================================
# INDIVIDUAL SUBJECT VERIFICATION
# =============================================================================

def verify_subject(subject_folder: str) -> dict:
    """
    Run all verification checks on a single subject's data.
    
    Args:
        subject_folder: Path to the subject's data folder
        
    Returns:
        Dict with verification results and flags
    """
    subject_number = os.path.basename(subject_folder)
    
    results = {
        'subject_number': subject_number,
        'folder_path': subject_folder,
        'timestamp': datetime.now().isoformat(),
        'questionnaires': {},
        'trial_blocks': {},
        'sleepiness': {},
        'consent': {},
        'flags': [],
        'warnings': [],
        'errors': [],
    }
    
    # Check questionnaires
    for q_name, expected_n in EXPECTED_QUESTIONS.items():
        q_result = _verify_questionnaire(subject_folder, q_name, subject_number, expected_n)
        results['questionnaires'][q_name] = q_result
        if q_result.get('missing_file'):
            results['errors'].append(f"Missing questionnaire: {q_name}")
        elif q_result.get('missing_questions'):
            results['warnings'].append(f"Incomplete questionnaire {q_name}: missing Q{q_result['missing_questions']}")
    
    # Check trial blocks
    for block_name in ['full_sentence', 'imagined_sentence']:
        block_result = _verify_trial_block(subject_folder, block_name, subject_number)
        results['trial_blocks'][block_name] = block_result
        if block_result.get('missing_file'):
            results['errors'].append(f"Missing trial data: {block_name}")
        else:
            # Check for bias
            if block_result.get('bias_percent', 0) > BIAS_THRESHOLD_PERCENT:
                results['flags'].append(f"HIGH_BIAS_{block_name.upper()}: {block_result['bias_percent']:.1f}%")
            # Check for fast responses
            if block_result.get('fast_responses', 0) > 0:
                results['warnings'].append(f"Fast responses in {block_name}: {block_result['fast_responses']} trials < {MIN_RT_MS}ms")
    
    # Check sleepiness data
    sleepiness_result = _verify_sleepiness(subject_folder, subject_number)
    results['sleepiness'] = sleepiness_result
    if sleepiness_result.get('missing_file'):
        results['warnings'].append("Missing sleepiness data")
    
    # Check consent
    consent_result = _verify_consent(subject_folder, subject_number)
    results['consent'] = consent_result
    if not consent_result.get('consented'):
        results['flags'].append("DID_NOT_CONSENT")
    
    # Global checks
    if len(results['errors']) > 0:
        results['flags'].append("HAS_ERRORS")
    if len(results['warnings']) > 3:
        results['flags'].append("MULTIPLE_WARNINGS")
    
    results['is_valid'] = len(results['errors']) == 0 and 'DID_NOT_CONSENT' not in results['flags']
    
    return results


def _verify_questionnaire(folder: str, q_name: str, subject_number: str, expected_n: int) -> dict:
    """Verify a single questionnaire file."""
    filepath = os.path.join(folder, f'{q_name}_{subject_number}.csv')
    
    if not os.path.exists(filepath):
        return {'missing_file': True, 'expected_questions': expected_n}
    
    try:
        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            lines = list(reader)
    except Exception as e:
        return {'error': str(e), 'expected_questions': expected_n}
    
    if len(lines) < 2:
        return {'error': 'No data rows', 'expected_questions': expected_n}
    
    header = lines[0]
    data_row = lines[1]
    
    # Count questions (excluding subject_number column)
    num_questions = len(header) - 1
    responses = data_row[1:]
    
    # Find missing/empty responses
    missing = []
    for i, r in enumerate(responses):
        if r == '' or r is None:
            missing.append(i + 1)
    
    return {
        'expected_questions': expected_n,
        'actual_questions': num_questions,
        'questions_match': num_questions == expected_n,
        'all_answered': len(missing) == 0,
        'num_answered': num_questions - len(missing),
        'missing_questions': missing if missing else None,
    }


def _verify_trial_block(folder: str, block_name: str, subject_number: str) -> dict:
    """Verify trial block data."""
    # Check both old format (flat) and new format (subfolder)
    filepath_flat = os.path.join(folder, f'{block_name}_{subject_number}.csv')
    filepath_subfolder = os.path.join(folder, block_name, f'{block_name}_{subject_number}.csv')
    
    filepath = filepath_subfolder if os.path.exists(filepath_subfolder) else filepath_flat
    
    if not os.path.exists(filepath):
        return {'missing_file': True}
    
    try:
        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            lines = list(reader)
    except Exception as e:
        return {'error': str(e)}
    
    if len(lines) < 2:
        return {'error': 'No trial data'}
    
    header = lines[0]
    trials = lines[1:]
    
    # Create index mapping
    indices = {col: i for i, col in enumerate(header)}
    
    # Count responses
    target_responses = 0
    distractor_responses = 0
    target_stimuli = 0
    distractor_stimuli = 0
    
    # Response times
    response_times_ms = []
    fast_responses = 0
    slow_responses = 0
    
    for trial in trials:
        stim_type = trial[indices.get('Stimulus Type', -1)] if 'Stimulus Type' in indices else None
        response = trial[indices.get('Subject Response', -1)] if 'Subject Response' in indices else None
        
        if stim_type == 'target':
            target_stimuli += 1
        elif stim_type == 'distractor':
            distractor_stimuli += 1
        
        if response == 'target':
            target_responses += 1
        elif response == 'distractor':
            distractor_responses += 1
        
        # Calculate response time
        if 'Audio End Timestamp' in indices and 'Subject Response Timestamp' in indices:
            try:
                audio_end = int(trial[indices['Audio End Timestamp']])
                response_time = int(trial[indices['Subject Response Timestamp']])
                rt_ns = response_time - audio_end
                rt_ms = rt_ns / 1_000_000  # Convert to milliseconds
                response_times_ms.append(rt_ms)
                
                if rt_ms < MIN_RT_MS:
                    fast_responses += 1
                elif rt_ms > MAX_RT_MS:
                    slow_responses += 1
            except (ValueError, TypeError):
                pass
    
    total_responses = target_responses + distractor_responses
    bias_percent = (max(target_responses, distractor_responses) / total_responses * 100) if total_responses > 0 else 0
    bias_direction = 'target' if target_responses > distractor_responses else 'distractor'
    
    # Signal detection metrics
    hits = sum(1 for t in trials if t[indices.get('Stimulus Type', -1)] == 'target' and t[indices.get('Subject Response', -1)] == 'target')
    misses = sum(1 for t in trials if t[indices.get('Stimulus Type', -1)] == 'target' and t[indices.get('Subject Response', -1)] == 'distractor')
    false_alarms = sum(1 for t in trials if t[indices.get('Stimulus Type', -1)] == 'distractor' and t[indices.get('Subject Response', -1)] == 'target')
    correct_rejections = sum(1 for t in trials if t[indices.get('Stimulus Type', -1)] == 'distractor' and t[indices.get('Subject Response', -1)] == 'distractor')
    
    hit_rate = hits / target_stimuli if target_stimuli > 0 else 0
    fa_rate = false_alarms / distractor_stimuli if distractor_stimuli > 0 else 0
    
    return {
        'num_trials': len(trials),
        'expected_trials': EXPECTED_TRIALS_PER_BLOCK.get(block_name, 'unknown'),
        'target_stimuli': target_stimuli,
        'distractor_stimuli': distractor_stimuli,
        'target_responses': target_responses,
        'distractor_responses': distractor_responses,
        'bias_percent': round(bias_percent, 1),
        'bias_direction': bias_direction,
        'hits': hits,
        'misses': misses,
        'false_alarms': false_alarms,
        'correct_rejections': correct_rejections,
        'hit_rate': round(hit_rate, 3),
        'false_alarm_rate': round(fa_rate, 3),
        'fast_responses': fast_responses,
        'slow_responses': slow_responses,
        'mean_rt_ms': round(sum(response_times_ms) / len(response_times_ms), 1) if response_times_ms else None,
        'min_rt_ms': round(min(response_times_ms), 1) if response_times_ms else None,
        'max_rt_ms': round(max(response_times_ms), 1) if response_times_ms else None,
    }


def _verify_sleepiness(folder: str, subject_number: str) -> dict:
    """Verify sleepiness data."""
    # Check both old and new filename formats
    filepath_old = os.path.join(folder, f'sleepiness_{subject_number}.csv')
    filepath_new = os.path.join(folder, f'stanford_sleepiness_{subject_number}.csv')
    
    filepath = filepath_new if os.path.exists(filepath_new) else filepath_old
    
    if not os.path.exists(filepath):
        return {'missing_file': True}
    
    try:
        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            lines = list(reader)
    except Exception as e:
        return {'error': str(e)}
    
    # Count measurements
    num_measurements = len(lines) - 1  # Exclude header
    
    return {
        'num_measurements': num_measurements,
        'expected_measurements': 4,  # 2 blocks x 2 (pre/post)
        'complete': num_measurements >= 4,
    }


def _verify_consent(folder: str, subject_number: str) -> dict:
    """Verify consent status."""
    filepath = os.path.join(folder, f'consent_{subject_number}.csv')
    
    if not os.path.exists(filepath):
        return {'missing_file': True}
    
    try:
        with open(filepath, 'r', newline='') as f:
            reader = csv.reader(f)
            lines = list(reader)
    except Exception as e:
        return {'error': str(e)}
    
    if len(lines) < 2:
        return {'error': 'No consent data'}
    
    header = lines[0]
    data = lines[1]
    indices = {col: i for i, col in enumerate(header)}
    
    consented = data[indices.get('Consented', -1)].lower() == 'true' if 'Consented' in indices else None
    
    return {
        'consented': consented,
        'has_signature': data[indices.get('Signature', -1)] != '' if 'Signature' in indices else None,
    }


# =============================================================================
# GLOBAL VERIFICATION (ALL SUBJECTS)
# =============================================================================

def verify_all_subjects(results_dir: str) -> dict:
    """
    Run verification on all subjects in the results directory.
    
    Returns:
        Dict with summary statistics and per-subject results
    """
    all_results = []
    
    for folder_name in os.listdir(results_dir):
        folder_path = os.path.join(results_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue
        # Skip non-numeric folders (like 'analysis')
        if not folder_name.isdigit():
            continue
        
        subject_result = verify_subject(folder_path)
        all_results.append(subject_result)
    
    # Calculate summary
    valid_subjects = [r for r in all_results if r['is_valid']]
    flagged_subjects = [r for r in all_results if r['flags']]
    
    # Aggregate bias stats
    bias_subjects = []
    for r in all_results:
        for block in ['full_sentence', 'imagined_sentence']:
            if block in r['trial_blocks'] and r['trial_blocks'][block].get('bias_percent', 0) > BIAS_THRESHOLD_PERCENT:
                bias_subjects.append({
                    'subject': r['subject_number'],
                    'block': block,
                    'bias_percent': r['trial_blocks'][block]['bias_percent'],
                    'bias_direction': r['trial_blocks'][block]['bias_direction'],
                })
    
    # Fast responders
    fast_responders = []
    for r in all_results:
        for block in ['full_sentence', 'imagined_sentence']:
            if block in r['trial_blocks'] and r['trial_blocks'][block].get('fast_responses', 0) > 5:
                fast_responders.append({
                    'subject': r['subject_number'],
                    'block': block,
                    'fast_responses': r['trial_blocks'][block]['fast_responses'],
                    'mean_rt_ms': r['trial_blocks'][block].get('mean_rt_ms'),
                })
    
    summary = {
        'total_subjects': len(all_results),
        'valid_subjects': len(valid_subjects),
        'invalid_subjects': len(all_results) - len(valid_subjects),
        'flagged_subjects': len(flagged_subjects),
        'subjects_with_bias': len(bias_subjects),
        'subjects_with_fast_responses': len(fast_responders),
        'bias_details': bias_subjects,
        'fast_responder_details': fast_responders,
        'all_flags': [{'subject': r['subject_number'], 'flags': r['flags']} for r in flagged_subjects],
    }
    
    return {
        'summary': summary,
        'subjects': all_results,
    }


def generate_verification_report(results_dir: str, output_path: str | None = None) -> str:
    """
    Generate a human-readable verification report.
    
    Args:
        results_dir: Path to results directory
        output_path: Optional path to save report. If None, prints to stdout.
        
    Returns:
        Report string
    """
    verification = verify_all_subjects(results_dir)
    summary = verification['summary']
    
    lines = [
        "=" * 70,
        "DATA VERIFICATION REPORT",
        f"Generated: {datetime.now().isoformat()}",
        "=" * 70,
        "",
        "SUMMARY",
        "-" * 40,
        f"Total subjects:              {summary['total_subjects']}",
        f"Valid subjects:              {summary['valid_subjects']}",
        f"Invalid subjects:            {summary['invalid_subjects']}",
        f"Flagged subjects:            {summary['flagged_subjects']}",
        f"Subjects with response bias: {summary['subjects_with_bias']}",
        f"Subjects with fast responses: {summary['subjects_with_fast_responses']}",
        "",
    ]
    
    if summary['bias_details']:
        lines.extend([
            "RESPONSE BIAS WARNINGS",
            "-" * 40,
        ])
        for b in summary['bias_details']:
            lines.append(f"  Subject {b['subject']}: {b['block']} - {b['bias_percent']:.1f}% {b['bias_direction']} responses")
        lines.append("")
    
    if summary['fast_responder_details']:
        lines.extend([
            "FAST RESPONSE WARNINGS",
            "-" * 40,
        ])
        for f in summary['fast_responder_details']:
            lines.append(f"  Subject {f['subject']}: {f['block']} - {f['fast_responses']} trials < {MIN_RT_MS}ms (mean: {f['mean_rt_ms']}ms)")
        lines.append("")
    
    if summary['all_flags']:
        lines.extend([
            "ALL FLAGS BY SUBJECT",
            "-" * 40,
        ])
        for f in summary['all_flags']:
            lines.append(f"  Subject {f['subject']}: {', '.join(f['flags'])}")
        lines.append("")
    
    lines.extend([
        "=" * 70,
        "END OF REPORT",
        "=" * 70,
    ])
    
    report = "\n".join(lines)
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"Report saved to: {output_path}")
    
    return report


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
    
    report = generate_verification_report(results_dir)
    print(report)
