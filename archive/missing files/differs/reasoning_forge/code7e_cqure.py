"""
Compatibility shim.

The real module is `reasoning_forge.codette_cqure`.  "Code7eCQURE" was a PDF
font-extraction artifact for "CodetteCQURE" (the 7 is the "tt" ligature); this
module keeps the old import path working for existing callers and citations.
"""

from reasoning_forge.codette_cqure import CodetteCQURE

Code7eCQURE = CodetteCQURE

__all__ = ["CodetteCQURE", "Code7eCQURE"]
