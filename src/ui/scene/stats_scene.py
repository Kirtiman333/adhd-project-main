"""
Progress dashboard scene — surfaces the focus-score trend the scorer produces.

Reads nothing itself; GameManager builds a ProgressReport via src/core/progress.py
and hands it to `show_report`, keeping the data layer testable and the scene thin.
"""

from src.ui.scene.scene import Scene
from src.ui.elements import MetricList, focus_bar
from src.config import SCREEN_WIDTH


class StatsScene(Scene):
    def __init__(self, name=None):
        super().__init__(name)
        self.create_button(["Back"], rect=(40, 40, 120))
        self.back_button = self.buttons[0]
        self.title = self.create_label("Your Focus Progress", rect=(SCREEN_WIDTH // 2 - 180, 40, 360))
        self.metrics = MetricList(self.manager, x=SCREEN_WIDTH // 2 - 280, y=120)

    def show_report(self, report, scored=None):
        lines = []
        if report is None or report.session_count == 0:
            lines.append("No sessions yet - play a game to start tracking your focus.")
        else:
            lines.append(f"Sessions played : {report.session_count}")
            lines.append(f"Best focus      : {report.best_score:.0f}/100")
            lines.append(f"Last focus      : {report.last_score:.0f}/100   {focus_bar(report.last_score)}")
            lines.append(f"Average         : {report.mean_score:.0f}/100")
            lines.append(f"Trend           : {report.trend}  ({'+' if report.delta >= 0 else ''}{report.delta})")
            lines.append("")
            lines.append("Recent sessions:")
            for label, score in report.per_session[-6:]:
                lines.append(f"  {label}   {score:5.1f}  {focus_bar(score)}")
        self.metrics.set_rows(lines)
