from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from errormentor.log_parser import ErrorEvent


@dataclass
class SpikeReport:
    error_type: str
    spike_started_at: datetime
    baseline_rate: float
    peak_rate: float
    acceleration_factor: float

class SpikeDetector:
    def detect(self, events: list[ErrorEvent]) -> Optional[SpikeReport]:
        if not events:
            return None

        # Filter to only ERROR level events with an error_type
        error_events = [e for e in events if e.level == "ERROR" and e.error_type]
        if not error_events:
            return None

        # Group by minute and error_type
        # min_bucket -> error_type -> count
        buckets = {}
        for e in error_events:
            # truncate to minute
            minute = e.timestamp.replace(second=0, microsecond=0)
            if minute not in buckets:
                buckets[minute] = {}
            if e.error_type not in buckets[minute]:
                buckets[minute][e.error_type] = 0
            buckets[minute][e.error_type] += 1

        if not buckets:
            return None

        sorted_minutes = sorted(buckets.keys())

        # We need to find if any minute has a spike compared to the previous 30 minutes
        for i, current_minute in enumerate(sorted_minutes):
            current_counts = buckets[current_minute]

            # Baseline: average rate over preceding 30 minutes
            start_baseline = current_minute - timedelta(minutes=30)

            baseline_counts = {}
            baseline_minutes_count = 0

            # Find all minutes in the 30 min window before current_minute
            for j in range(i - 1, -1, -1):
                prev_minute = sorted_minutes[j]
                if prev_minute < start_baseline:
                    break
                baseline_minutes_count += 1
                for err_type, count in buckets[prev_minute].items():
                    baseline_counts[err_type] = baseline_counts.get(err_type, 0) + count

            # We need at least some history? The spec says "baseline: average rate over preceding 30 minutes".
            # Let's say if we don't have 30 mins, we just use whatever we have up to 30 mins.
            # If baseline_minutes_count is 0, we can't really say it's a spike (or maybe we say baseline is 0?).
            # Let's assume a minimum baseline of 0.1 for division safety if baseline is 0

            window_size = max(baseline_minutes_count, 1) # avoid div by 0 if using minutes, but spec says "rate", maybe per minute?
            # Actually if we have 30 min window, the rate is total / 30. If we only have 5 mins of logs before this, rate is total / 5?
            # Let's use the actual time difference or 1 minute if it's the first log.

            for err_type, peak_count in current_counts.items():
                baseline_total = baseline_counts.get(err_type, 0)

                # If we have 0 baseline, any peak is a spike. Let's say baseline rate is 0.
                baseline_rate = baseline_total / window_size if baseline_minutes_count > 0 else 0.1
                peak_rate = peak_count  # count in this 1 minute

                # Spike threshold: current minute rate > 3x baseline
                if peak_rate > 3 * baseline_rate and peak_rate > 1: # at least > 1 to avoid 1 error being a spike
                    return SpikeReport(
                        error_type=err_type,
                        spike_started_at=current_minute,
                        baseline_rate=baseline_rate,
                        peak_rate=peak_rate,
                        acceleration_factor=peak_rate / baseline_rate
                    )

        return None
