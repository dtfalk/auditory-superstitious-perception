"""
Compare Forced Alignment Results from Multiple Tools - Multi-Run Analysis

This script loads the summary JSON output from each alignment tool and compares:
1. WITHIN-METHOD consistency (how stable is each tool across runs)
2. ACROSS-METHOD consistency (how much do tools agree with each other)
"""

import os
import sys
import json

# =============================================================================
# CONFIGURATION
# =============================================================================

TARGET_WORD = "wall"

# =============================================================================
# PATHS - matches the output structure from individual scripts
# =============================================================================

BASE_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BASE_DIR, "results")

TOOL_DIRS = {
    "Whisper": os.path.join(RESULTS_DIR, "whisper"),
    "WhisperX": os.path.join(RESULTS_DIR, "whisperx"),
    "Gentle": os.path.join(RESULTS_DIR, "gentle"),
    "MFA": os.path.join(RESULTS_DIR, "mfa"),
    "NeMo": os.path.join(RESULTS_DIR, "nemo"),
    "WebMAUS": os.path.join(RESULTS_DIR, "webmaus"),
}

# =============================================================================


def load_summary(tool_name, audio_name="fullsentence"):
    """Load the summary JSON file for a tool."""
    tool_dir = TOOL_DIRS.get(tool_name)
    if not tool_dir or not os.path.exists(tool_dir):
        return None
    
    summary_path = os.path.join(tool_dir, f"{audio_name}_summary.json")
    if not os.path.exists(summary_path):
        return None
    
    with open(summary_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_within_method_summary(summaries):
    """Print within-method consistency for each tool."""
    print("\n" + "="*80)
    print("  WITHIN-METHOD CONSISTENCY (how stable is each tool across runs)")
    print("="*80)
    
    print(f"\n  {'Tool':<12} {'N':>4} {'Start Mean':>12} {'Start Std':>10} {'End Mean':>12} {'End Std':>10}")
    print(f"  {'-'*12} {'-'*4} {'-'*12} {'-'*10} {'-'*12} {'-'*10}")
    
    for tool_name, summary in summaries.items():
        stats = summary.get("statistics")
        if not stats:
            print(f"  {tool_name:<12} {'N/A':>4} {'N/A':>12} {'N/A':>10} {'N/A':>12} {'N/A':>10}")
            continue
        
        n = stats.get("n_successful_runs", 0)
        start = stats.get("start_ms", {})
        end = stats.get("end_ms", {})
        
        print(f"  {tool_name:<12} {n:>4} {start.get('mean', 0):>10.2f}ms {start.get('std', 0):>8.2f}ms {end.get('mean', 0):>10.2f}ms {end.get('std', 0):>8.2f}ms")
    
    # Rank by consistency (lowest std deviation)
    print("\n  WITHIN-METHOD RANKING (by Start Time Std Dev - lower is more consistent):")
    
    tool_stds = []
    for tool_name, summary in summaries.items():
        stats = summary.get("statistics")
        if stats and stats.get("start_ms"):
            tool_stds.append((tool_name, stats["start_ms"].get("std", float('inf'))))
    
    tool_stds.sort(key=lambda x: x[1])
    for rank, (tool_name, std) in enumerate(tool_stds, 1):
        print(f"    {rank}. {tool_name}: {std:.2f}ms std")


def calculate_across_method_stats(summaries):
    """Calculate statistics comparing tools to each other."""
    # Collect mean values from each tool
    tool_means = {}
    
    for tool_name, summary in summaries.items():
        stats = summary.get("statistics")
        if stats:
            tool_means[tool_name] = {
                "start_ms": stats.get("start_ms", {}).get("mean"),
                "end_ms": stats.get("end_ms", {}).get("mean"),
                "duration_ms": stats.get("duration_ms", {}).get("mean")
            }
    
    if len(tool_means) < 2:
        return None
    
    # Calculate cross-tool statistics
    starts = [m["start_ms"] for m in tool_means.values() if m["start_ms"] is not None]
    ends = [m["end_ms"] for m in tool_means.values() if m["end_ms"] is not None]
    durations = [m["duration_ms"] for m in tool_means.values() if m["duration_ms"] is not None]
    
    def calc_range_stats(values):
        if not values:
            return None
        mean = sum(values) / len(values)
        return {
            "mean": mean,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "std": (sum((x - mean)**2 for x in values) / len(values)) ** 0.5
        }
    
    return {
        "tools": list(tool_means.keys()),
        "tool_means": tool_means,
        "start_ms": calc_range_stats(starts),
        "end_ms": calc_range_stats(ends),
        "duration_ms": calc_range_stats(durations)
    }


def print_across_method_summary(across_stats, summaries):
    """Print across-method consistency analysis."""
    if not across_stats:
        print("\n  Need at least 2 tools with results for across-method comparison.")
        return
    
    print("\n" + "="*80)
    print("  ACROSS-METHOD CONSISTENCY (how much do tools agree with each other)")
    print("="*80)
    
    print(f"\n  Mean values from each tool for '{TARGET_WORD}':")
    print(f"\n  {'Tool':<12} {'Start':>12} {'End':>12} {'Duration':>12}")
    print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
    
    for tool_name, means in across_stats["tool_means"].items():
        print(f"  {tool_name:<12} {means['start_ms']:>10.2f}ms {means['end_ms']:>10.2f}ms {means['duration_ms']:>10.2f}ms")
    
    # Cross-tool statistics
    print(f"\n  CROSS-TOOL STATISTICS:")
    
    for metric_name, metric_key in [("Start Time", "start_ms"), ("End Time", "end_ms"), ("Duration", "duration_ms")]:
        m = across_stats[metric_key]
        if m:
            print(f"\n  {metric_name}:")
            print(f"    Mean of means: {m['mean']:.2f} ms")
            print(f"    Range:         {m['range']:.2f} ms (min: {m['min']:.2f}, max: {m['max']:.2f})")
            print(f"    Std Dev:       {m['std']:.2f} ms")
    
    # Pairwise comparison
    tools = across_stats["tools"]
    means = across_stats["tool_means"]
    
    print(f"\n  PAIRWISE DIFFERENCES (absolute difference between tool means):")
    print(f"\n  {'Comparison':<25} {'Start Diff':>12} {'End Diff':>12}")
    print(f"  {'-'*25} {'-'*12} {'-'*12}")
    
    for i, t1 in enumerate(tools):
        for j, t2 in enumerate(tools):
            if i < j:
                start_diff = abs(means[t1]["start_ms"] - means[t2]["start_ms"])
                end_diff = abs(means[t1]["end_ms"] - means[t2]["end_ms"])
                print(f"  {t1} vs {t2:<12} {start_diff:>10.2f}ms {end_diff:>10.2f}ms")


def print_verdict(across_stats):
    """Print overall verdict on alignment quality."""
    if not across_stats:
        return
    
    print("\n" + "="*80)
    print("  VERDICT")
    print("="*80)
    
    start_range = across_stats["start_ms"]["range"] if across_stats["start_ms"] else 0
    end_range = across_stats["end_ms"]["range"] if across_stats["end_ms"] else 0
    max_range = max(start_range, end_range)
    
    if max_range < 10:
        verdict = "EXCELLENT"
        desc = "All tools agree within 10ms. High confidence in alignment."
    elif max_range < 30:
        verdict = "GOOD"
        desc = "Tools agree within 30ms (human perception threshold ~25ms)."
    elif max_range < 50:
        verdict = "ACCEPTABLE"
        desc = "Some variation (30-50ms). Use mean values or prefer MFA/Gentle."
    else:
        verdict = "POOR"
        desc = "Significant disagreement (>50ms). Consider manual verification."
    
    print(f"\n  AGREEMENT LEVEL: {verdict}")
    print(f"  Max cross-tool range: {max_range:.1f}ms")
    print(f"  {desc}")
    
    # Best estimate
    print("\n" + "-"*80)
    print("  CONSENSUS ESTIMATE (mean of all tool means)")
    print("-"*80)
    
    print(f"\n  Word: '{TARGET_WORD}'")
    if across_stats["start_ms"]:
        print(f"  Start:    {across_stats['start_ms']['mean']:.2f} ms ({across_stats['start_ms']['mean']/1000:.3f} s)")
    if across_stats["end_ms"]:
        print(f"  End:      {across_stats['end_ms']['mean']:.2f} ms ({across_stats['end_ms']['mean']/1000:.3f} s)")
    if across_stats["duration_ms"]:
        print(f"  Duration: {across_stats['duration_ms']['mean']:.2f} ms")


def save_comparison_report(summaries, across_stats, output_path):
    """Save complete comparison report to JSON."""
    # Ensure directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    report = {
        "target_word": TARGET_WORD,
        "tools_analyzed": list(summaries.keys()),
        "within_method": {},
        "across_method": across_stats
    }
    
    for tool_name, summary in summaries.items():
        report["within_method"][tool_name] = summary.get("statistics")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n  Report saved to: {output_path}")


def main():
    print("="*80)
    print("  FORCED ALIGNMENT COMPARISON - MULTI-RUN ANALYSIS")
    print("="*80)
    
    # Check if results directory exists
    if not os.path.exists(RESULTS_DIR):
        print(f"\n  ERROR: Results directory not found: {RESULTS_DIR}")
        print("\n  Run the individual alignment scripts first:")
        print("    python align_with_whisper.py")
        print("    python align_with_gentle.py   (requires Docker)")
        print("    python align_with_mfa.py      (requires conda activate mfa)")
        return
    
    # Load summaries from each tool
    print("\n  Loading results...")
    summaries = {}
    
    for tool_name in TOOL_DIRS:
        summary = load_summary(tool_name, "fullsentence")
        if summary:
            print(f"    {tool_name}: Loaded ({summary.get('n_runs', '?')} runs)")
            summaries[tool_name] = summary
        else:
            print(f"    {tool_name}: NOT FOUND")
    
    if not summaries:
        print("\n  ERROR: No results found!")
        print("\n  Run at least one alignment script first.")
        return
    
    # Within-method analysis
    print_within_method_summary(summaries)
    
    # Across-method analysis
    across_stats = None
    if len(summaries) >= 2:
        across_stats = calculate_across_method_stats(summaries)
        print_across_method_summary(across_stats, summaries)
        print_verdict(across_stats)
    else:
        print("\n  Only 1 tool found - skipping across-method comparison.")
        print("  Run more alignment scripts for cross-tool analysis.")
    
    # Save report to root of forced_alignment folder
    report_path = os.path.join(BASE_DIR, "alignment_comparison_report.json")
    save_comparison_report(summaries, across_stats, report_path)
    
    # Also save to results folder for consistency
    report_path_results = os.path.join(RESULTS_DIR, "comparison_report.json")
    save_comparison_report(summaries, across_stats, report_path_results)
    
    print("\n" + "="*80)
    print("  COMPARISON COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
