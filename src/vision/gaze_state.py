from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class GazeState:
    """
    data class store state in gazeEstimate
    """
    pred_x: Optional[float] = None
    pred_y: Optional[float] = None
    blink_detected: Optional[bool] = None
    cursor_alpha: float = 0.0
    contours: List = field(default_factory=list) # only for kde filter