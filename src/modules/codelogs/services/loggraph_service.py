"""
LogGraphService — comprehensive log visualization and statistics.

Generates error frequency charts, time-based trend data, summary statistics,
anomaly detection, file size distribution, log source correlation, and
growth rate analysis for log files across discovered paths.

:project: CodeCortex
:package: Codelogs.Services
:author: Steeven Andrian
:copyright: (c) 2026 CODDY Codework
:standard: CODDY-Codelogs-v2.0
"""
from __future__ import annotations

import logging
import os
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Set

from src.modules.codelogs.services.log_service import LogService, LogSearchFilter

logger = logging.getLogger("CodeCortex.Codelogs.LogGraph")


class LogGraphService:
    """Generate comprehensive log visualization data."""

    def __init__(self, log_service: Optional[LogService] = None):
        self._log_service = log_service or LogService()

    @property
    def log_service(self) -> LogService:
        return self._log_service

    def generate(self, days: int = 7, file_pattern: str = "*.log",
                 max_files: int = 50, search_paths: Optional[str] = None,
                 detect_language: bool = True, detect_os: bool = True,
                 detect_servers: bool = True, detect_databases: bool = True) -> Dict[str, Any]:
        """Generate comprehensive graph data from logs within the specified time window.

        Auto-indexes via LogService._ensure_log_roots() when no roots found.
        """
        roots = self._log_service._ensure_log_roots(search_paths)
        if not roots:
            return {"error": "No log directories or files found. Ensure project_root is set and contains log files."}

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        yesterday = datetime.now(tz=timezone.utc) - timedelta(hours=24)

        # Metrics accumulators
        level_counter: Counter = Counter()
        hour_buckets: Counter = Counter()
        date_buckets: Counter = Counter()
        weekday_buckets: Counter = Counter()
        error_message_counter: Counter = Counter()
        file_error_counter: Counter = Counter()
        file_size_counter: Counter = Counter()
        file_line_counter: Counter = Counter()
        unique_messages: Set[str] = set()
        total_lines = 0
        total_files = 0
        errors_last_24h = 0
        errors_last_1h = 0
        source_timeline: Dict[str, List[float]] = defaultdict(list)
        level_over_time: Dict[str, Counter] = defaultdict(Counter)
        anomaly_scores: Dict[str, float] = {}
        first_ts: Optional[datetime] = None
        last_ts: Optional[datetime] = None
        error_files: Set[str] = set()
        total_errors_baseline = 0

        one_hour_ago = datetime.now(tz=timezone.utc) - timedelta(hours=1)

        for root in roots:
            for r, dirs, files in os.walk(root):
                for fname in files:
                    if total_files >= max_files:
                        break
                    if not self._log_service._is_log_file(fname):
                        continue
                    fpath = os.path.join(r, fname)
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(fpath), tz=timezone.utc)
                        if mtime < cutoff:
                            continue
                    except Exception:
                        continue
                    lines = self._log_service._read_log_file(fpath)
                    if lines is None:
                        continue
                    total_files += 1
                    file_size_counter[fpath] = os.path.getsize(fpath)
                    file_line_counter[fpath] = len(lines)
                    file_error_counter[fpath] = 0
                    rel_path = os.path.relpath(fpath, self._log_service._project_root) if self._log_service._project_root else fpath

                    for line in lines:
                        stripped = line.strip()
                        if not stripped:
                            continue
                        total_lines += 1
                        level = self._log_service._parse_log_level(stripped)
                        level_counter[level] += 1
                        ts = self._log_service._parse_timestamp(stripped)

                        if ts:
                            try:
                                ts_dt = self._parse_ts_to_dt(ts)
                                if ts_dt:
                                    if first_ts is None or ts_dt < first_ts:
                                        first_ts = ts_dt
                                    if last_ts is None or ts_dt > last_ts:
                                        last_ts = ts_dt

                                    hour_key = ts_dt.strftime("%Y-%m-%dT%H:00")
                                    hour_buckets[hour_key] += 1
                                    date_key = ts_dt.strftime("%Y-%m-%d")
                                    date_buckets[date_key] += 1
                                    weekday_key = ts_dt.strftime("%A")
                                    weekday_buckets[weekday_key] += 1

                                    level_over_time[date_key][level] += 1
                                    source_timeline[rel_path].append(ts_dt.timestamp())

                                    now = datetime.now(tz=timezone.utc)
                                    if ts_dt > now - timedelta(hours=24):
                                        errors_last_24h += 1 if level in ("ERROR", "CRITICAL", "FATAL") else 0
                                    if ts_dt > one_hour_ago:
                                        errors_last_1h += 1 if level in ("ERROR", "CRITICAL", "FATAL") else 0
                            except Exception:
                                pass

                        if level in ("ERROR", "CRITICAL", "FATAL"):
                            msg_key = stripped[:120]
                            error_message_counter[msg_key] += 1
                            file_error_counter[fpath] += 1
                            error_files.add(rel_path)
                            total_errors_baseline += 1
                            unique_messages.add(stripped[:200])

        # ── Metrics Computation ──────────────────────────────────────

        # 1. Error frequency
        total_errors = level_counter.get("ERROR", 0) + level_counter.get("CRITICAL", 0) + level_counter.get("FATAL", 0)
        total_warnings = level_counter.get("WARN", 0) + level_counter.get("WARNING", 0)
        total_info = level_counter.get("INFO", 0)
        total_debug = level_counter.get("DEBUG", 0)
        total_trace = level_counter.get("TRACE", 0)

        # 2. Top errors
        top_errors = [
            {"message": msg, "count": count}
            for msg, count in error_message_counter.most_common(20)
        ]

        # 3. File size distribution
        file_sizes = list(file_size_counter.values())
        size_distribution = {
            "tiny_under_1kb": sum(1 for s in file_sizes if s < 1024),
            "small_1kb_10kb": sum(1 for s in file_sizes if 1024 <= s < 10240),
            "medium_10kb_100kb": sum(1 for s in file_sizes if 10240 <= s < 102400),
            "large_100kb_1mb": sum(1 for s in file_sizes if 102400 <= s < 1048576),
            "huge_over_1mb": sum(1 for s in file_sizes if s >= 1048576),
        }

        # 4. File-level error correlation
        top_error_files = sorted(
            [(rel_path, count) for fpath, count in file_error_counter.items()
             if count > 0 and (rel_path := os.path.relpath(fpath, self._log_service._project_root) if self._log_service._project_root else fpath)],
            key=lambda x: x[1],
            reverse=True,
        )[:15]
        top_error_files_clean = [
            {"file": f[0], "error_count": f[1]} for f in top_error_files
        ]

        # 5. Growth rate (lines per hour)
        growth_rate = {}
        if first_ts and last_ts and total_lines > 0:
            hours_span = max((last_ts - first_ts).total_seconds() / 3600, 0.1)
            growth_rate = {
                "total_hours_span": round(hours_span, 1),
                "lines_per_hour": round(total_lines / hours_span, 1),
                "errors_per_hour": round(total_errors / hours_span, 1),
                "warnings_per_hour": round(total_warnings / hours_span, 1),
            }

        # 6. Weekday distribution
        weekday_distribution = dict(weekday_buckets.most_common())

        # 7. Unique error messages count
        unique_error_count = len(unique_messages)

        # 8. Error rate (% of total lines)
        error_rate = round((total_errors / max(total_lines, 1)) * 100, 2)
        warning_rate = round((total_warnings / max(total_lines, 1)) * 100, 2)

        # 9. Spike detection (anomaly detection using z-score on hourly buckets)
        hourly_counts = [v for _, v in sorted(hour_buckets.items())]
        spikes = []
        if len(hourly_counts) >= 3:
            try:
                mean = statistics.mean(hourly_counts)
                stdev = statistics.stdev(hourly_counts) if len(hourly_counts) > 1 else 0
                if stdev > 0:
                    for bucket_key, count in sorted(hour_buckets.items()):
                        z = (count - mean) / stdev
                        if z > 2.0:
                            spikes.append({
                                "bucket": bucket_key,
                                "count": count,
                                "z_score": round(z, 2),
                                "severity": "high" if z > 3.0 else "medium",
                            })
            except Exception:
                pass

        # 10. Level summary over time (finds days with concentrated errors)
        error_peaks = []
        for date_key, lc in sorted(level_over_time.items()):
            day_errors = lc.get("ERROR", 0) + lc.get("CRITICAL", 0) + lc.get("FATAL", 0)
            day_total = sum(lc.values())
            if day_total > 0:
                error_pct = round((day_errors / day_total) * 100, 1)
                if error_pct > 50:
                    error_peaks.append({
                        "date": date_key,
                        "error_percentage": error_pct,
                        "total_lines": day_total,
                        "error_count": day_errors,
                    })

        # Convert time buckets
        sorted_hours = sorted(hour_buckets.items())
        sorted_dates = sorted(date_buckets.items())

        return {
            "summary": {
                "total_files": total_files,
                "total_lines": total_lines,
                "time_window_days": days,
                "errors_last_24h": errors_last_24h,
                "errors_last_1h": errors_last_1h,
                "unique_error_messages": unique_error_count,
                "error_rate_percent": error_rate,
                "warning_rate_percent": warning_rate,
                "files_with_errors": len(error_files),
                "timespan": {
                    "first_log": first_ts.isoformat() if first_ts else None,
                    "last_log": last_ts.isoformat() if last_ts else None,
                },
            },
            "level_distribution": dict(level_counter.most_common()),
            "error_frequency": {
                "total_errors": total_errors,
                "total_warnings": total_warnings,
                "total_info": total_info,
                "total_debug": total_debug,
                "total_trace": total_trace,
                "total_critical": level_counter.get("CRITICAL", 0),
                "total_fatal": level_counter.get("FATAL", 0),
            },
            "time_trend": {
                "hourly": [{"bucket": k, "count": v} for k, v in sorted_hours],
                "daily": [{"bucket": k, "count": v} for k, v in sorted_dates],
            },
            "weekday_distribution": weekday_distribution,
            "growth_rate": growth_rate,
            "file_size_distribution": size_distribution,
            "file_error_correlation": top_error_files_clean,
            "top_error_messages": top_errors,
            "anomaly_spikes": spikes[:20] if spikes else [],
            "error_peaks": error_peaks[:10] if error_peaks else [],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def error_frequency(self, days: int = 7, file_pattern: str = "*.log",
                        max_files: int = 50, search_paths: Optional[str] = None) -> Dict[str, Any]:
        data = self.generate(days=days, file_pattern=file_pattern,
                             max_files=max_files, search_paths=search_paths)
        if "error" in data:
            return data
        return {
            "error_frequency": data.get("error_frequency", {}),
            "level_distribution": data.get("level_distribution", {}),
            "summary": data.get("summary", {}),
        }

    def time_trend(self, days: int = 7, granularity: str = "hourly",
                   file_pattern: str = "*.log", max_files: int = 50,
                   search_paths: Optional[str] = None) -> Dict[str, Any]:
        data = self.generate(days=days, file_pattern=file_pattern,
                             max_files=max_files, search_paths=search_paths)
        if "error" in data:
            return data
        trend = data.get("time_trend", {})
        if granularity == "daily":
            return {"trend": trend.get("daily", []), "granularity": "daily"}
        return {"trend": trend.get("hourly", []), "granularity": "hourly"}

    def summary(self, days: int = 7, file_pattern: str = "*.log",
                max_files: int = 50, search_paths: Optional[str] = None) -> Dict[str, Any]:
        data = self.generate(days=days, file_pattern=file_pattern,
                             max_files=max_files, search_paths=search_paths)
        if "error" in data:
            return data
        return {
            "summary": data.get("summary", {}),
            "error_frequency": data.get("error_frequency", {}),
            "level_distribution": data.get("level_distribution", {}),
            "top_error_messages": data.get("top_error_messages", [])[:10],
            "anomaly_spikes": data.get("anomaly_spikes", [])[:5],
            "growth_rate": data.get("growth_rate", {}),
        }

    def anomalies(self, days: int = 7, file_pattern: str = "*.log",
                  max_files: int = 50, search_paths: Optional[str] = None) -> Dict[str, Any]:
        data = self.generate(days=days, file_pattern=file_pattern,
                             max_files=max_files, search_paths=search_paths)
        if "error" in data:
            return data
        return {
            "anomaly_spikes": data.get("anomaly_spikes", []),
            "error_peaks": data.get("error_peaks", []),
            "summary": data.get("summary", {}),
        }

    def files(self, days: int = 7, max_files: int = 50,
              search_paths: Optional[str] = None) -> Dict[str, Any]:
        data = self.generate(days=days, max_files=max_files, search_paths=search_paths)
        if "error" in data:
            return data
        return {
            "file_size_distribution": data.get("file_size_distribution", {}),
            "file_error_correlation": data.get("file_error_correlation", []),
            "growth_rate": data.get("growth_rate", {}),
        }

    def health(self, days: int = 7, file_pattern: str = "*.log",
               max_files: int = 50, search_paths: Optional[str] = None) -> Dict[str, Any]:
        """Log health assessment — returns a simplified health score and key metrics."""
        data = self.generate(days=days, file_pattern=file_pattern,
                             max_files=max_files, search_paths=search_paths)
        if "error" in data:
            return data

        s = data.get("summary", {})
        ef = data.get("error_frequency", {})
        spikes = data.get("anomaly_spikes", [])

        total_lines = s.get("total_lines", 0)
        total_errors = ef.get("total_errors", 0)
        errors_24h = s.get("errors_last_24h", 0)
        spike_count = len(spikes)

        health_score = 100
        weight_error_rate = 30
        weight_recent_errors = 30
        weight_spikes = 40

        # Deduct for high error rate
        if total_lines > 0:
            err_rate = total_errors / total_lines
            health_score -= min(weight_error_rate, int(err_rate * 100 * weight_error_rate))

        # Deduct for recent errors
        health_score -= min(weight_recent_errors, errors_24h * 2)

        # Deduct for anomaly spikes
        health_score -= min(weight_spikes, spike_count * 5)

        status = "healthy" if health_score >= 80 else "degraded" if health_score >= 50 else "critical"

        return {
            "health_score": max(0, health_score),
            "status": status,
            "total_errors_24h": errors_24h,
            "anomaly_spikes_detected": spike_count,
            "error_rate": round((total_errors / max(total_lines, 1)) * 100, 2),
            "total_lines_scanned": total_lines,
            "total_files_scanned": s.get("total_files", 0),
        }

    def discover(self, custom_paths: Optional[str] = None,
                 detect_language: bool = True, detect_os: bool = True,
                 detect_servers: bool = True, detect_databases: bool = True,
                 detect_dev_tools: bool = True,
                 max_results: int = 200) -> Dict[str, Any]:
        """Discover log files across all detected paths."""
        if not self._log_service._project_root:
            return {"error": "No project root set"}
        collector = self._log_service.path_collector
        files = collector.discover_log_files(
            custom_paths=custom_paths,
            max_results=max_results,
            detect_language=detect_language,
            detect_os=detect_os,
            detect_servers=detect_servers,
            detect_databases=detect_databases,
            detect_dev_tools=detect_dev_tools,
        )
        search_paths = collector.collect_paths(
            custom_paths=custom_paths,
            detect_language=detect_language,
            detect_os=detect_os,
            detect_servers=detect_servers,
            detect_databases=detect_databases,
            detect_dev_tools=detect_dev_tools,
        )
        detected_languages = collector._detect_languages()
        detected_servers = collector._detect_servers()
        detected_databases = collector._detect_databases()
        detected_os = collector._detect_os()
        detected_dev_tools_list = collector._detect_local_dev_tools()

        total_size = sum(f.get("size_bytes", 0) for f in files)
        return {
            "project_root": self._log_service._project_root,
            "total_files": len(files),
            "total_size_bytes": total_size,
            "total_size_display": collector._format_size(total_size) if hasattr(collector, '_format_size') else str(total_size),
            "search_paths_scanned": search_paths[:50],
            "files": files[:max_results],
            "detection": {
                "operating_system": detected_os,
                "languages": detected_languages,
                "servers": detected_servers,
                "databases": detected_databases,
                "local_dev_tools": detected_dev_tools_list,
                "custom_paths": custom_paths.split(",") if custom_paths else [],
            },
        }

    def _parse_ts_to_dt(self, ts: str) -> Optional[datetime]:
        for fmt in [
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S.%f",
            "%d/%b/%Y:%H:%M:%S",
            "%b %d %H:%M:%S",
        ]:
            try:
                clean = ts.strip()
                if clean.endswith("Z"):
                    clean = clean[:-1]
                if "+" in clean:
                    clean = clean.rsplit("+", 1)[0]
                elif "-" in clean[10:]:
                    parts = clean.rsplit("-", 1)
                    if len(parts[1]) == 5 and ":" in parts[1]:
                        clean = parts[0]
                try:
                    return datetime.strptime(clean[:len(datetime.now().strftime(fmt))], fmt).replace(tzinfo=timezone.utc)
                except Exception:
                    continue
            except Exception:
                continue
        return None
