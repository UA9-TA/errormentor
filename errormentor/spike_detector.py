from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict

from .log_parser import ErrorEvent


@dataclass
class SpikeReport:
    error_type: str
    spike_started_at: datetime
    baseline_rate: float  # errors per minute
    peak_rate: float      # errors per minute
    acceleration_factor: float


class SpikeDetector:
    def __init__(self, window_size_minutes: int = 1, baseline_minutes: int = 30, threshold: float = 3.0):
        self.window_size_minutes = window_size_minutes
        self.baseline_minutes = baseline_minutes
        self.threshold = threshold

    def detect(self, events: list[ErrorEvent]) -> Optional[SpikeReport]:
        if not events:
            return None

        # Sort events by time just in case
        events.sort(key=lambda x: x.timestamp)

        # Bucket events by error type
        events_by_type = defaultdict(list)
        for event in events:
            # Group by error_type, or just message if no error_type
            key = event.error_type if event.error_type else event.message
            if key:
                 events_by_type[key].append(event)

        best_spike = None

        for error_type, type_events in events_by_type.items():
            spike = self._detect_for_type(error_type, type_events)
            if spike:
                if best_spike is None or spike.acceleration_factor > best_spike.acceleration_factor:
                    best_spike = spike

        return best_spike

    def _detect_for_type(self, error_type: str, events: list[ErrorEvent]) -> Optional[SpikeReport]:
        if not events:
            return None

        # Group by minute
        buckets = defaultdict(int)
        for event in events:
            # Round down to nearest minute
            minute = event.timestamp.replace(second=0, microsecond=0)
            buckets[minute] += 1

        if not buckets:
            return None

        sorted_minutes = sorted(buckets.keys())

        # Analyze each minute to see if it's a spike compared to previous baseline_minutes
        for i, current_minute in enumerate(sorted_minutes):
            current_rate = buckets[current_minute]

            # Calculate baseline
            baseline_start = current_minute - timedelta(minutes=self.baseline_minutes)
            baseline_events = 0
            baseline_window_count = 0

            # Only look at the actual minutes leading up to current_minute
            for j in range(1, self.baseline_minutes + 1):
                past_minute = current_minute - timedelta(minutes=j)
                if past_minute >= sorted_minutes[0]:
                    baseline_events += buckets[past_minute]
                    baseline_window_count += 1

            # If we don't have enough history, use what we have, but be careful of div by zero
            if baseline_window_count == 0:
                continue

            baseline_rate = baseline_events / baseline_window_count

            # If baseline is 0, we can't calculate a factor, but any rate > 0 is technically an infinite spike.
            # We'll use a small epsilon to avoid div by zero if we want, or just require a minimum baseline.
            # Let's say if baseline is very low, we require a minimum absolute rate to consider it a spike.
            effective_baseline = max(baseline_rate, 0.5) # Prevent dividing by zero and triggering on tiny numbers

            acceleration = current_rate / effective_baseline

            if acceleration >= self.threshold and current_rate >= 2: # Require at least 2 events in a minute to call it a spike
                return SpikeReport(
                    error_type=error_type,
                    spike_started_at=current_minute,
                    baseline_rate=round(baseline_rate, 2),
                    peak_rate=round(current_rate, 2),
                    acceleration_factor=round(acceleration, 2)
                )

        return None
