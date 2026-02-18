"""
Analysis Runner
===============
Main entry point for running all analysis scripts.

Usage:
    python -m analysis.run_analysis --verify          # Run data verification
    python -m analysis.run_analysis --individual 123  # Analyze subject 123
    python -m analysis.run_analysis --global          # Global analysis
    python -m analysis.run_analysis --export          # Export to CSV
    python -m analysis.run_analysis --all             # Run all analyses
"""

import argparse
import os
import sys

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.data_verification import verify_all_subjects, generate_verification_report, verify_subject
from analysis.individual_analysis import analyze_subject, save_subject_report
from analysis.global_analysis import analyze_all_subjects, generate_global_report, export_to_csv
from analysis.scoring import score_questionnaire, score_all_subjects, get_scoring_preset


def get_results_dir() -> str:
    """Get the results directory path."""
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'results')


def get_analysis_output_dir() -> str:
    """Get/create the analysis output directory."""
    output_dir = os.path.join(get_results_dir(), 'analysis_output')
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def run_verification(save_report: bool = True) -> None:
    """Run data verification on all subjects."""
    print("Running data verification...")
    results_dir = get_results_dir()
    
    if save_report:
        output_path = os.path.join(get_analysis_output_dir(), 'verification_report.txt')
        report = generate_verification_report(results_dir, output_path)
    else:
        report = generate_verification_report(results_dir)
    
    print(report)


def run_individual_analysis(subject_number: str, save_report: bool = True) -> None:
    """Run analysis on a single subject."""
    print(f"Analyzing subject {subject_number}...")
    results_dir = get_results_dir()
    subject_folder = os.path.join(results_dir, subject_number)
    
    if not os.path.exists(subject_folder):
        print(f"Error: Subject folder not found: {subject_folder}")
        return
    
    if save_report:
        output_path = os.path.join(get_analysis_output_dir(), f'subject_{subject_number}_report.txt')
        report = save_subject_report(subject_folder, output_path)
        print(f"Report saved to: {output_path}")
    else:
        report = save_subject_report(subject_folder)
    
    print(report)


def run_global_analysis(save_report: bool = True) -> None:
    """Run global analysis on all subjects."""
    print("Running global analysis...")
    results_dir = get_results_dir()
    
    if save_report:
        output_path = os.path.join(get_analysis_output_dir(), 'global_analysis_report.txt')
        report = generate_global_report(results_dir, output_path)
    else:
        report = generate_global_report(results_dir)
    
    print(report)


def run_export() -> None:
    """Export data to CSV files."""
    print("Exporting data to CSV...")
    results_dir = get_results_dir()
    output_dir = os.path.join(get_analysis_output_dir(), 'csv_exports')
    
    exports = export_to_csv(results_dir, output_dir)
    
    print("\nExported files:")
    for name, path in exports.items():
        print(f"  {name}: {path}")


def run_all() -> None:
    """Run all analyses."""
    run_verification()
    print("\n" + "=" * 70 + "\n")
    run_global_analysis()
    print("\n" + "=" * 70 + "\n")
    run_export()


def main():
    parser = argparse.ArgumentParser(description='Run data analysis scripts')
    parser.add_argument('--verify', action='store_true', help='Run data verification')
    parser.add_argument('--individual', type=str, metavar='SUBJECT', help='Analyze specific subject')
    parser.add_argument('--global', dest='run_global', action='store_true', help='Run global analysis')
    parser.add_argument('--export', action='store_true', help='Export to CSV')
    parser.add_argument('--all', action='store_true', help='Run all analyses')
    parser.add_argument('--no-save', action='store_true', help='Print reports without saving')
    
    args = parser.parse_args()
    
    save = not args.no_save
    
    if args.all:
        run_all()
    elif args.verify:
        run_verification(save)
    elif args.individual:
        run_individual_analysis(args.individual, save)
    elif args.run_global:
        run_global_analysis(save)
    elif args.export:
        run_export()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
