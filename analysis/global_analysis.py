"""
Global Analysis Module
======================
Aggregate analysis across all subjects:
- Group statistics
- Questionnaire distributions
- Performance comparisons
- Export to dataframes
"""

import csv
import os
import math
from datetime import datetime
from typing import Any

from .scoring import score_all_subjects, get_scoring_preset
from .individual_analysis import analyze_subject


def analyze_all_subjects(results_dir: str) -> dict:
    """
    Run analysis on all subjects and compute aggregate statistics.
    
    Args:
        results_dir: Path to results directory
        
    Returns:
        Dict with global analysis results
    """
    all_analyses = []
    
    for folder_name in os.listdir(results_dir):
        folder_path = os.path.join(results_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue
        if not folder_name.isdigit():
            continue
        
        try:
            analysis = analyze_subject(folder_path)
            all_analyses.append(analysis)
        except Exception as e:
            print(f"Error analyzing {folder_name}: {e}")
    
    if not all_analyses:
        return {'error': 'No subjects found'}
    
    results = {
        'n_subjects': len(all_analyses),
        'analysis_timestamp': datetime.now().isoformat(),
        'questionnaire_stats': _compute_questionnaire_stats(all_analyses),
        'block_stats': _compute_block_stats(all_analyses),
        'individual_summaries': [
            {
                'subject_number': a['subject_number'],
                **a['summary'],
            }
            for a in all_analyses
        ],
    }
    
    return results


def _compute_questionnaire_stats(analyses: list[dict]) -> dict:
    """Compute aggregate statistics for each questionnaire."""
    questionnaire_names = ['tellegen', 'vhq', 'launay_slade', 'bais_c', 'bais_v',
                           'dissociative_experiences', 'flow_state_scale']
    
    stats = {}
    
    for q_name in questionnaire_names:
        scores = []
        means = []
        
        for analysis in analyses:
            q_data = analysis.get('questionnaire_scores', {}).get(q_name)
            if q_data and q_data.get('complete'):
                scores.append(q_data['total_score'])
                means.append(q_data['mean_score'])
        
        if scores:
            stats[q_name] = {
                'n_complete': len(scores),
                'n_total': len(analyses),
                'completion_rate': round(len(scores) / len(analyses), 3),
                'total_score': {
                    'mean': round(sum(scores) / len(scores), 2),
                    'std': round(_std(scores), 2),
                    'min': min(scores),
                    'max': max(scores),
                },
                'mean_score': {
                    'mean': round(sum(means) / len(means), 3),
                    'std': round(_std(means), 3),
                    'min': round(min(means), 3),
                    'max': round(max(means), 3),
                },
            }
        else:
            stats[q_name] = {'n_complete': 0, 'n_total': len(analyses)}
    
    return stats


def _compute_block_stats(analyses: list[dict]) -> dict:
    """Compute aggregate statistics for trial blocks."""
    block_names = ['full_sentence', 'imagined_sentence']
    
    stats = {}
    
    for block_name in block_names:
        dprimes = []
        criterions = []
        accuracies = []
        hit_rates = []
        fa_rates = []
        mean_rts = []
        
        for analysis in analyses:
            block_data = analysis.get('blocks', {}).get(block_name)
            if block_data:
                dprimes.append(block_data['dprime'])
                criterions.append(block_data['criterion'])
                accuracies.append(block_data['accuracy'])
                hit_rates.append(block_data['hit_rate'])
                fa_rates.append(block_data['false_alarm_rate'])
                if block_data.get('rt_stats', {}).get('mean'):
                    mean_rts.append(block_data['rt_stats']['mean'])
        
        if dprimes:
            stats[block_name] = {
                'n_subjects': len(dprimes),
                'dprime': {
                    'mean': round(sum(dprimes) / len(dprimes), 3),
                    'std': round(_std(dprimes), 3),
                    'min': round(min(dprimes), 3),
                    'max': round(max(dprimes), 3),
                },
                'criterion': {
                    'mean': round(sum(criterions) / len(criterions), 3),
                    'std': round(_std(criterions), 3),
                },
                'accuracy': {
                    'mean': round(sum(accuracies) / len(accuracies) * 100, 1),
                    'std': round(_std(accuracies) * 100, 1),
                },
                'hit_rate': {
                    'mean': round(sum(hit_rates) / len(hit_rates) * 100, 1),
                    'std': round(_std(hit_rates) * 100, 1),
                },
                'false_alarm_rate': {
                    'mean': round(sum(fa_rates) / len(fa_rates) * 100, 1),
                    'std': round(_std(fa_rates) * 100, 1),
                },
                'rt_ms': {
                    'mean': round(sum(mean_rts) / len(mean_rts), 1) if mean_rts else None,
                    'std': round(_std(mean_rts), 1) if mean_rts else None,
                },
            }
    
    return stats


def _std(values: list) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================

def export_to_csv(results_dir: str, output_dir: str | None = None) -> dict:
    """
    Export all subject data to CSV files for external analysis.
    
    Creates:
    - questionnaire_scores.csv: All questionnaire totals
    - block_performance.csv: All block performance metrics
    - trial_data_combined.csv: All trial data combined
    
    Args:
        results_dir: Path to results directory
        output_dir: Output directory (defaults to results_dir/exports)
        
    Returns:
        Dict with paths to created files
    """
    if output_dir is None:
        output_dir = os.path.join(results_dir, 'exports')
    os.makedirs(output_dir, exist_ok=True)
    
    created_files = {}
    
    # Export questionnaire scores
    q_path = _export_questionnaire_scores(results_dir, output_dir)
    if q_path:
        created_files['questionnaire_scores'] = q_path
    
    # Export block performance
    b_path = _export_block_performance(results_dir, output_dir)
    if b_path:
        created_files['block_performance'] = b_path
    
    # Export combined trial data
    t_path = _export_trial_data(results_dir, output_dir)
    if t_path:
        created_files['trial_data'] = t_path
    
    return created_files


def _export_questionnaire_scores(results_dir: str, output_dir: str) -> str | None:
    """Export all questionnaire scores to a single CSV."""
    questionnaires = ['tellegen', 'vhq', 'launay_slade', 'bais_c', 'bais_v',
                      'dissociative_experiences', 'flow_state_scale']
    
    all_data = []
    
    for folder_name in os.listdir(results_dir):
        folder_path = os.path.join(results_dir, folder_name)
        if not os.path.isdir(folder_path) or not folder_name.isdigit():
            continue
        
        row = {'subject_number': folder_name}
        
        for q_name in questionnaires:
            filepath = os.path.join(folder_path, f'{q_name}_{folder_name}.csv')
            if os.path.exists(filepath):
                preset = get_scoring_preset(q_name)
                from .scoring import score_questionnaire
                score = score_questionnaire(filepath, **preset)
                row[f'{q_name}_total'] = score['total_score']
                row[f'{q_name}_mean'] = score['mean_score']
                row[f'{q_name}_complete'] = score['num_answered'] == score['num_questions']
            else:
                row[f'{q_name}_total'] = ''
                row[f'{q_name}_mean'] = ''
                row[f'{q_name}_complete'] = False
        
        all_data.append(row)
    
    if not all_data:
        return None
    
    filepath = os.path.join(output_dir, 'questionnaire_scores.csv')
    
    header = ['subject_number']
    for q in questionnaires:
        header.extend([f'{q}_total', f'{q}_mean', f'{q}_complete'])
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(all_data)
    
    return filepath


def _export_block_performance(results_dir: str, output_dir: str) -> str | None:
    """Export block performance metrics to CSV."""
    all_data = []
    
    for folder_name in os.listdir(results_dir):
        folder_path = os.path.join(results_dir, folder_name)
        if not os.path.isdir(folder_path) or not folder_name.isdigit():
            continue
        
        analysis = analyze_subject(folder_path)
        
        for block_name, block_data in analysis.get('blocks', {}).items():
            row = {
                'subject_number': folder_name,
                'block': block_name,
                'num_trials': block_data['num_trials'],
                'hits': block_data['hits'],
                'misses': block_data['misses'],
                'false_alarms': block_data['false_alarms'],
                'correct_rejections': block_data['correct_rejections'],
                'hit_rate': block_data['hit_rate'],
                'false_alarm_rate': block_data['false_alarm_rate'],
                'dprime': block_data['dprime'],
                'criterion': block_data['criterion'],
                'accuracy': block_data['accuracy'],
                'mean_rt_ms': block_data.get('rt_stats', {}).get('mean', ''),
                'std_rt_ms': block_data.get('rt_stats', {}).get('std', ''),
            }
            all_data.append(row)
    
    if not all_data:
        return None
    
    filepath = os.path.join(output_dir, 'block_performance.csv')
    
    header = ['subject_number', 'block', 'num_trials', 'hits', 'misses', 
              'false_alarms', 'correct_rejections', 'hit_rate', 'false_alarm_rate',
              'dprime', 'criterion', 'accuracy', 'mean_rt_ms', 'std_rt_ms']
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(all_data)
    
    return filepath


def _export_trial_data(results_dir: str, output_dir: str) -> str | None:
    """Export all trial data to a single CSV."""
    all_trials = []
    
    for folder_name in os.listdir(results_dir):
        folder_path = os.path.join(results_dir, folder_name)
        if not os.path.isdir(folder_path) or not folder_name.isdigit():
            continue
        
        for block_name in ['full_sentence', 'imagined_sentence']:
            filepath_flat = os.path.join(folder_path, f'{block_name}_{folder_name}.csv')
            filepath_sub = os.path.join(folder_path, block_name, f'{block_name}_{folder_name}.csv')
            filepath = filepath_sub if os.path.exists(filepath_sub) else filepath_flat
            
            if not os.path.exists(filepath):
                continue
            
            with open(filepath, 'r', newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    all_trials.append(row)
    
    if not all_trials:
        return None
    
    filepath = os.path.join(output_dir, 'trial_data_combined.csv')
    
    # Get all unique columns
    all_cols = set()
    for trial in all_trials:
        all_cols.update(trial.keys())
    header = sorted(all_cols)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(all_trials)
    
    return filepath


def generate_global_report(results_dir: str, output_path: str | None = None) -> str:
    """
    Generate a comprehensive global analysis report.
    
    Args:
        results_dir: Path to results directory
        output_path: Optional path to save report
        
    Returns:
        Report string
    """
    analysis = analyze_all_subjects(results_dir)
    
    lines = [
        "=" * 70,
        "GLOBAL ANALYSIS REPORT",
        f"Generated: {analysis['analysis_timestamp']}",
        f"Total Subjects: {analysis['n_subjects']}",
        "=" * 70,
        "",
    ]
    
    # Questionnaire stats
    if analysis['questionnaire_stats']:
        lines.extend([
            "QUESTIONNAIRE STATISTICS",
            "-" * 50,
        ])
        for q_name, stats in analysis['questionnaire_stats'].items():
            if stats.get('n_complete', 0) > 0:
                total = stats['total_score']
                lines.extend([
                    f"  {q_name}:",
                    f"    Completed: {stats['n_complete']}/{stats['n_total']} ({stats['completion_rate']*100:.0f}%)",
                    f"    Total Score: M={total['mean']}, SD={total['std']}, Range=[{total['min']}, {total['max']}]",
                ])
        lines.append("")
    
    # Block stats
    if analysis['block_stats']:
        lines.extend([
            "BLOCK PERFORMANCE STATISTICS",
            "-" * 50,
        ])
        for block_name, stats in analysis['block_stats'].items():
            lines.extend([
                f"  {block_name} (n={stats['n_subjects']}):",
                f"    d': M={stats['dprime']['mean']}, SD={stats['dprime']['std']}",
                f"    Criterion: M={stats['criterion']['mean']}, SD={stats['criterion']['std']}",
                f"    Accuracy: M={stats['accuracy']['mean']}%, SD={stats['accuracy']['std']}%",
                f"    Hit Rate: M={stats['hit_rate']['mean']}%, SD={stats['hit_rate']['std']}%",
                f"    FA Rate: M={stats['false_alarm_rate']['mean']}%, SD={stats['false_alarm_rate']['std']}%",
            ])
            if stats['rt_ms']['mean']:
                lines.append(f"    RT: M={stats['rt_ms']['mean']}ms, SD={stats['rt_ms']['std']}ms")
            lines.append("")
    
    lines.extend([
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
    
    # Generate report
    report = generate_global_report(results_dir)
    print(report)
    
    # Export to CSV
    print("\nExporting to CSV...")
    exports = export_to_csv(results_dir)
    for name, path in exports.items():
        print(f"  {name}: {path}")
