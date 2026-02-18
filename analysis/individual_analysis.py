"""
Individual Subject Analysis Module
==================================
Detailed analysis for a single subject including:
- All questionnaire scores
- Signal detection metrics (d', criterion)
- Response time distributions
- Trial-by-trial data
"""

import csv
import os
import math
from datetime import datetime
from typing import Any

from .scoring import score_questionnaire, get_scoring_preset


def analyze_subject(subject_folder: str) -> dict:
    """
    Run comprehensive analysis on a single subject.
    
    Args:
        subject_folder: Path to subject's data folder
        
    Returns:
        Dict with all analysis results
    """
    subject_number = os.path.basename(subject_folder)
    
    results = {
        'subject_number': subject_number,
        'analysis_timestamp': datetime.now().isoformat(),
        'questionnaire_scores': {},
        'blocks': {},
        'sleepiness': {},
        'summary': {},
    }
    
    # Score all questionnaires
    questionnaires = ['tellegen', 'vhq', 'launay_slade', 'bais_c', 'bais_v', 
                      'dissociative_experiences', 'flow_state_scale']
    
    for q_name in questionnaires:
        filepath = os.path.join(subject_folder, f'{q_name}_{subject_number}.csv')
        if os.path.exists(filepath):
            preset = get_scoring_preset(q_name)
            score = score_questionnaire(filepath, **preset)
            results['questionnaire_scores'][q_name] = {
                'total_score': score['total_score'],
                'mean_score': score['mean_score'],
                'num_answered': score['num_answered'],
                'num_questions': score['num_questions'],
                'complete': score['num_answered'] == score['num_questions'],
            }
    
    # Analyze trial blocks
    for block_name in ['full_sentence', 'imagined_sentence']:
        block_result = _analyze_trial_block(subject_folder, block_name, subject_number)
        if block_result:
            results['blocks'][block_name] = block_result
    
    # Analyze sleepiness
    sleepiness = _analyze_sleepiness(subject_folder, subject_number)
    if sleepiness:
        results['sleepiness'] = sleepiness
    
    # Create summary
    results['summary'] = _create_summary(results)
    
    return results


def _analyze_trial_block(folder: str, block_name: str, subject_number: str) -> dict | None:
    """Analyze a single trial block in detail."""
    # Check both formats
    filepath_flat = os.path.join(folder, f'{block_name}_{subject_number}.csv')
    filepath_subfolder = os.path.join(folder, block_name, f'{block_name}_{subject_number}.csv')
    filepath = filepath_subfolder if os.path.exists(filepath_subfolder) else filepath_flat
    
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r', newline='') as f:
        reader = csv.reader(f)
        lines = list(reader)
    
    if len(lines) < 2:
        return None
    
    header = lines[0]
    trials = lines[1:]
    indices = {col: i for i, col in enumerate(header)}
    
    # Signal detection counts
    hits = 0
    misses = 0
    false_alarms = 0
    correct_rejections = 0
    
    # Response times
    rts = []
    
    for trial in trials:
        stim_type = trial[indices.get('Stimulus Type', -1)]
        response = trial[indices.get('Subject Response', -1)]
        
        if stim_type == 'target' and response == 'target':
            hits += 1
        elif stim_type == 'target' and response == 'distractor':
            misses += 1
        elif stim_type == 'distractor' and response == 'target':
            false_alarms += 1
        elif stim_type == 'distractor' and response == 'distractor':
            correct_rejections += 1
        
        # Calculate RT
        if 'Audio End Timestamp' in indices and 'Subject Response Timestamp' in indices:
            try:
                audio_end = int(trial[indices['Audio End Timestamp']])
                resp_time = int(trial[indices['Subject Response Timestamp']])
                rt_ms = (resp_time - audio_end) / 1_000_000
                if rt_ms > 0:
                    rts.append(rt_ms)
            except (ValueError, TypeError):
                pass
    
    # Calculate rates
    n_targets = hits + misses
    n_distractors = false_alarms + correct_rejections
    
    hit_rate = hits / n_targets if n_targets > 0 else 0
    fa_rate = false_alarms / n_distractors if n_distractors > 0 else 0
    
    # Correct extreme rates for d' calculation
    hit_rate_adj = _adjust_rate(hit_rate, n_targets)
    fa_rate_adj = _adjust_rate(fa_rate, n_distractors)
    
    # Calculate d' and criterion
    dprime = _calculate_dprime(hit_rate_adj, fa_rate_adj)
    criterion = _calculate_criterion(hit_rate_adj, fa_rate_adj)
    
    # RT statistics
    rt_stats = {}
    if rts:
        rts_sorted = sorted(rts)
        rt_stats = {
            'mean': round(sum(rts) / len(rts), 1),
            'median': round(rts_sorted[len(rts) // 2], 1),
            'min': round(min(rts), 1),
            'max': round(max(rts), 1),
            'std': round(_std(rts), 1),
            'percentile_25': round(rts_sorted[int(len(rts) * 0.25)], 1),
            'percentile_75': round(rts_sorted[int(len(rts) * 0.75)], 1),
        }
    
    return {
        'num_trials': len(trials),
        'n_targets': n_targets,
        'n_distractors': n_distractors,
        'hits': hits,
        'misses': misses,
        'false_alarms': false_alarms,
        'correct_rejections': correct_rejections,
        'hit_rate': round(hit_rate, 3),
        'false_alarm_rate': round(fa_rate, 3),
        'dprime': round(dprime, 3),
        'criterion': round(criterion, 3),
        'accuracy': round((hits + correct_rejections) / len(trials), 3) if trials else 0,
        'response_bias': round((hits + false_alarms) / len(trials), 3) if trials else 0.5,  # Tendency to say "target"
        'rt_stats': rt_stats,
    }


def _adjust_rate(rate: float, n: int) -> float:
    """Adjust extreme rates (0 or 1) for d' calculation using log-linear correction."""
    if rate == 0:
        return 0.5 / n
    elif rate == 1:
        return (n - 0.5) / n
    return rate


def _calculate_dprime(hit_rate: float, fa_rate: float) -> float:
    """Calculate d' (d-prime) sensitivity measure."""
    from scipy.stats import norm
    z_hit = norm.ppf(hit_rate)
    z_fa = norm.ppf(fa_rate)
    return z_hit - z_fa


def _calculate_criterion(hit_rate: float, fa_rate: float) -> float:
    """Calculate criterion (c) bias measure."""
    from scipy.stats import norm
    z_hit = norm.ppf(hit_rate)
    z_fa = norm.ppf(fa_rate)
    return -0.5 * (z_hit + z_fa)


def _std(values: list) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def _analyze_sleepiness(folder: str, subject_number: str) -> dict | None:
    """Analyze sleepiness data across blocks."""
    filepath_old = os.path.join(folder, f'sleepiness_{subject_number}.csv')
    filepath_new = os.path.join(folder, f'stanford_sleepiness_{subject_number}.csv')
    filepath = filepath_new if os.path.exists(filepath_new) else filepath_old
    
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r', newline='') as f:
        reader = csv.reader(f)
        lines = list(reader)
    
    if len(lines) < 2:
        return None
    
    header = lines[0]
    
    # New format has one row per measurement
    if 'block_index' in header or 'pre_or_post' in header:
        measurements = []
        indices = {col: i for i, col in enumerate(header)}
        for row in lines[1:]:
            measurements.append({
                'block_index': row[indices.get('block_index', 0)],
                'block_scheme': row[indices.get('block_scheme', '')],
                'timing': row[indices.get('pre_or_post', '')],
                'response': row[indices.get('response', '')],
            })
        return {'measurements': measurements}
    else:
        # Old format has all in one row
        data = lines[1]
        return {'raw_data': data}


def _create_summary(results: dict) -> dict:
    """Create summary statistics for the subject."""
    summary = {}
    
    # Questionnaire summary
    q_scores = results.get('questionnaire_scores', {})
    if q_scores:
        summary['questionnaires_completed'] = sum(1 for q in q_scores.values() if q.get('complete', False))
        summary['questionnaires_total'] = len(q_scores)
    
    # Block summary
    blocks = results.get('blocks', {})
    if blocks:
        total_dprime = sum(b['dprime'] for b in blocks.values() if 'dprime' in b)
        summary['mean_dprime'] = round(total_dprime / len(blocks), 3) if blocks else 0
        summary['total_trials'] = sum(b['num_trials'] for b in blocks.values())
        summary['overall_accuracy'] = round(
            sum(b['hits'] + b['correct_rejections'] for b in blocks.values()) / 
            sum(b['num_trials'] for b in blocks.values()), 3
        ) if summary['total_trials'] > 0 else 0
    
    return summary


def save_subject_report(subject_folder: str, output_path: str | None = None) -> str:
    """
    Generate and optionally save a subject report.
    
    Args:
        subject_folder: Path to subject's data folder
        output_path: Optional path to save report
        
    Returns:
        Report string
    """
    analysis = analyze_subject(subject_folder)
    
    lines = [
        "=" * 60,
        f"SUBJECT ANALYSIS REPORT: {analysis['subject_number']}",
        f"Generated: {analysis['analysis_timestamp']}",
        "=" * 60,
        "",
    ]
    
    # Questionnaires
    if analysis['questionnaire_scores']:
        lines.extend([
            "QUESTIONNAIRE SCORES",
            "-" * 40,
        ])
        for q_name, scores in analysis['questionnaire_scores'].items():
            status = "✓" if scores['complete'] else "!"
            lines.append(f"  {q_name}: {scores['total_score']} (mean: {scores['mean_score']}) {status}")
        lines.append("")
    
    # Trial blocks
    if analysis['blocks']:
        lines.extend([
            "TRIAL PERFORMANCE",
            "-" * 40,
        ])
        for block_name, block in analysis['blocks'].items():
            lines.extend([
                f"  {block_name}:",
                f"    Trials: {block['num_trials']}",
                f"    d': {block['dprime']}",
                f"    Criterion: {block['criterion']}",
                f"    Accuracy: {block['accuracy'] * 100:.1f}%",
                f"    Hit Rate: {block['hit_rate'] * 100:.1f}%",
                f"    FA Rate: {block['false_alarm_rate'] * 100:.1f}%",
            ])
            if block['rt_stats']:
                lines.append(f"    Mean RT: {block['rt_stats']['mean']}ms (SD: {block['rt_stats']['std']})")
            lines.append("")
    
    # Summary
    if analysis['summary']:
        lines.extend([
            "SUMMARY",
            "-" * 40,
        ])
        for key, value in analysis['summary'].items():
            lines.append(f"  {key}: {value}")
        lines.append("")
    
    lines.extend([
        "=" * 60,
    ])
    
    report = "\n".join(lines)
    
    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)
    
    return report


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')
    
    # Analyze first available subject
    for folder in os.listdir(results_dir):
        folder_path = os.path.join(results_dir, folder)
        if os.path.isdir(folder_path) and folder.isdigit():
            report = save_subject_report(folder_path)
            print(report)
            break
