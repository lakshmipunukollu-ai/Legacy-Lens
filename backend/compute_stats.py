import os
import json
from pathlib import Path
from datetime import datetime

CODEBASE_DIR = Path(__file__).parent.parent / "codebase"
OUTPUT_FILE = Path(__file__).parent / "codebase_stats.json"
EXTENSIONS = {".cob", ".cbl", ".cpy"}

def compute_stats():
    files = []
    total_loc = 0
    pattern_counts = {
        "File I/O Operations": 0,
        "Error Handling": 0,
        "PERFORM Statements": 0,
        "Data Division": 0,
        "MOVE Statements": 0
    }

    # Walk codebase
    for root, dirs, filenames in os.walk(CODEBASE_DIR):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in filenames:
            if Path(fname).suffix.lower() in EXTENSIONS:
                fpath = Path(root) / fname
                try:
                    content = fpath.read_text(encoding='utf-8', errors='ignore')
                    lines = content.splitlines()
                    loc = len(lines)
                    total_loc += loc

                    # Count patterns
                    upper = content.upper()
                    pattern_counts["File I/O Operations"] += upper.count("OPEN ") + upper.count("CLOSE ") + upper.count("READ ") + upper.count("WRITE ")
                    pattern_counts["Error Handling"] += upper.count("ON ERROR") + upper.count("INVALID KEY") + upper.count("AT END") + upper.count("EXCEPTION")
                    pattern_counts["PERFORM Statements"] += upper.count("PERFORM ")
                    pattern_counts["Data Division"] += upper.count("DATA DIVISION") + upper.count("WORKING-STORAGE")
                    pattern_counts["MOVE Statements"] += upper.count("MOVE ")

                    files.append({"file": fname, "path": str(fpath), "loc": loc})
                except Exception as e:
                    print(f"Skipping {fname}: {e}")

    # Sort files by LOC descending
    files.sort(key=lambda x: x["loc"], reverse=True)
    top_files = [{"file": f["file"], "loc": f["loc"], "chunks": max(1, f["loc"] // 50)} for f in files[:10]]

    # Calculate health score based on real metrics
    avg_loc = total_loc / len(files) if files else 0
    perform_density = pattern_counts["PERFORM Statements"] / len(files) if files else 0
    error_ratio = pattern_counts["Error Handling"] / max(pattern_counts["PERFORM Statements"], 1)

    # Score: penalize very large files, reward error handling, penalize deep nesting
    health_score = 100
    if avg_loc > 500: health_score -= 15
    if avg_loc > 1000: health_score -= 10
    if perform_density > 50: health_score -= 10
    if error_ratio < 0.1: health_score -= 15
    if error_ratio > 0.3: health_score += 5

    # Build health notes based on real data
    health_notes = []
    if avg_loc > 500:
        health_notes.append(f"High average file size ({avg_loc:.0f} LOC/file) — refactoring recommended")
    if perform_density > 50:
        health_notes.append(f"High PERFORM density ({perform_density:.0f}/file) — deep call chains detected")
    if error_ratio < 0.1:
        health_notes.append("Low error handling coverage — less than 10% of PERFORMs have error handling")
    if len(files) > 400:
        health_notes.append(f"Large codebase ({len(files)} files) — consider modularization")

    # Check if one file dominates
    if files:
        max_file_loc = files[0]["loc"]
        dominant_pct = max_file_loc / total_loc * 100
        if dominant_pct > 50:
            health_score -= 20
            health_notes.insert(0, f"⚠️ {files[0]['file']} contains {dominant_pct:.0f}% of all LOC — extreme concentration risk")

    health_score = max(0, min(100, health_score))

    if not health_notes:
        health_notes.append("Codebase structure looks reasonable")

    stats = {
        "computed_at": datetime.now().isoformat(),
        "total_files": len(files),
        "total_loc": total_loc,
        "avg_loc_per_file": round(avg_loc, 1),
        "top_files": top_files,
        "patterns_summary": [
            {"pattern": k, "count": v} for k, v in pattern_counts.items()
        ],
        "health_score": health_score,
        "health_notes": health_notes,
        "languages": [
            {"name": "COBOL", "files": len(files), "percentage": 100}
        ]
    }

    OUTPUT_FILE.write_text(json.dumps(stats, indent=2))
    print(f"Stats computed and saved to {OUTPUT_FILE}")
    print(f"Files: {len(files)}, LOC: {total_loc:,}, Health Score: {health_score}")
    return stats

if __name__ == "__main__":
    compute_stats()
