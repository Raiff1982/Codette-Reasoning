
import re
import logging

class InputSanitizer:
    """Sanitize and inspect strings for newline‑based injection or other malicious patterns."""

    # Patterns that represent injection‑style line breaks or encoded variants
    _newline_patterns = [
        r"\\n",          # literal newline escape
        r"\\r",          # carriage return escape
        r"&#x0a;",         # HTML entity for LF
        r"&#x0d;",         # HTML entity for CR
        r"%0a",            # URL encoded LF
        r"%0d"            # URL encoded CR
    ]
    _compiled_newline = re.compile('|'.join(_newline_patterns), re.IGNORECASE)

    # Additional simple blacklist words (expand as needed)
    _blacklist = [
        r"<script",        # script tags
        r"<iframe",        # iframe tags
        r";--",            # SQL comment injection
    ]
    _compiled_black = re.compile('|'.join(_blacklist), re.IGNORECASE)

    def sanitize(self, text: str) -> str:
        """Remove dangerous patterns and log incidents."""
        original = text
        # Strip encoded newlines
        text = self._compiled_newline.sub(' ', text)
        # Strip obvious blacklist
        text = self._compiled_black.sub('[REDACTED]', text)

        if text != original:
            logging.warning("Input sanitized due to suspicious patterns")
        return text

    def detect(self, text: str) -> bool:
        """Return True if malicious pattern detected."""
        return bool(self._compiled_newline.search(text) or self._compiled_black.search(text))
