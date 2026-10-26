"""
aura.harness - Low-Level OS Execution & Safety Runtime
Encapsulates sensory perception, hardware actuation, UI automation, safety governors, and stealth shields.
"""

from aura.harness.perception import PERCEPTION, PerceptionHarness
from aura.harness.actuation import ACTUATION, ActuationHarness
from aura.harness.uia import UIA, UIAutomationHarness
from aura.harness.safety import SAFETY, SafetyHarness
from aura.harness.stealth import STEALTH, StealthHarness

__all__ = [
    "PERCEPTION", "PerceptionHarness",
    "ACTUATION", "ActuationHarness",
    "UIA", "UIAutomationHarness",
    "SAFETY", "SafetyHarness",
    "STEALTH", "StealthHarness"
]
