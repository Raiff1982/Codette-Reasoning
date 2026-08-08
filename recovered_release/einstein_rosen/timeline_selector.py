"""
Recovered from the Codette archives — see RECOVERY_MANIFEST.md
"""

def select_timeline_based_on_adrenaline(events, adrenaline_level):
    threshold = 1.0
    if adrenaline_level >= threshold:
        return [e for e in events if e['priority'] == 'high']
    return [e for e in events if e['priority'] != 'high']