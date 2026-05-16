"""Rich terminal dashboard for NOC Whisperer alerts, incidents, and advisories."""

from __future__ import annotations

import time
from datetime import timezone
from typing import List

from rich.columns import Columns
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from adapters.canonical_alert import CanonicalAlert, Incident


class NOCDashboard:
    """Three-panel rich dashboard showing alert stream, incident board, and advisory text."""

    def __init__(self) -> None:
        """Initialize dashboard state buffers."""
        self.alert_stream: List[CanonicalAlert] = []
        self.open_incidents: List[Incident] = []
        self.latest_advisory: str = ""
        self._stop = False

    def update_alert_stream(self, alert: CanonicalAlert) -> None:
        """Append alert and keep only the latest 10 events."""
        self.alert_stream.append(alert)
        self.alert_stream = self.alert_stream[-10:]

    def update_incident_board(self, incident: Incident) -> None:
        """Insert or update one incident in the open incident board state."""
        for idx, existing in enumerate(self.open_incidents):
            if existing.incident_id == incident.incident_id:
                if incident.status != "open":
                    self.open_incidents.pop(idx)
                else:
                    self.open_incidents[idx] = incident
                return
        if incident.status == "open":
            self.open_incidents.append(incident)

    def update_advisory(self, advisory_text: str) -> None:
        """Set the latest NOC advisory text."""
        self.latest_advisory = advisory_text

    def _alert_table(self) -> Table:
        """Build raw alert stream table."""
        table = Table(show_header=True, header_style="bold red")
        table.add_column("Time")
        table.add_column("Source")
        table.add_column("Device")
        table.add_column("Signal")
        for alert in self.alert_stream:
            ts = alert.timestamp
            if ts.tzinfo is not None:
                ts = ts.astimezone(timezone.utc)
            table.add_row(
                ts.strftime("%H:%M:%S"),
                alert.source_system,
                alert.device,
                alert.metric,
            )
        return table

    def _incident_table(self) -> Table:
        """Build incident board table."""
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("ID")
        table.add_column("Root Cause")
        table.add_column("Affected")
        table.add_column("Conf")
        table.add_column("Status")
        for incident in self.open_incidents:
            table.add_row(
                incident.incident_id[:8],
                incident.root_cause_device,
                ",".join(incident.affected_services[:3]),
                f"{incident.confidence:.2f}",
                incident.status,
            )
        return table

    def generate_display(self) -> Columns:
        """Return 3-column rich layout with alerts, incidents, and advisory panels."""
        panel1 = Panel(self._alert_table(), title="RAW ALERT STREAM", border_style="red")
        panel2 = Panel(self._incident_table(), title="INCIDENT BOARD", border_style="yellow")
        advisory_text = self.latest_advisory or "No advisories yet."
        panel3 = Panel(advisory_text, title="NOC ADVISORY", border_style="green")
        return Columns([panel1, panel2, panel3])

    def run(self) -> None:
        """Render the dashboard continuously at 2 Hz refresh rate."""
        with Live(self.generate_display(), refresh_per_second=2) as live:
            while not self._stop:
                live.update(self.generate_display())
                time.sleep(0.5)

    def stop(self) -> None:
        self._stop = True
