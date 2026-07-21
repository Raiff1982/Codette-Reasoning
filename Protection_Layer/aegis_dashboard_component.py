#!/usr/bin/env python3
"""
AEGIS Dashboard Component for Codette Web UI
Adds metrics display to the existing Codette dashboard.

This generates the HTML/CSS/JS to display AEGIS protection layer metrics
as a tab in the existing Codette web UI.

Author: Jonathan Harrison
"""

AEGIS_DASHBOARD_COMPONENT = """
<!-- AEGIS Metrics Dashboard Tab -->
<div id="aegis-metrics-tab" style="display:none; padding: 20px;">
  <div style="max-width: 1400px; margin: 0 auto;">
    
    <!-- Header -->
    <div style="margin-bottom: 30px; padding: 20px; background: rgba(74, 158, 255, 0.1); border-left: 4px solid #4a9eff; border-radius: 8px;">
      <h2 style="font-size: 2em; color: #4a9eff; margin-bottom: 10px;">🛡️ AEGIS Protection Layers</h2>
      <p style="color: #a0a0a0;">Real-time monitoring of ForgeEngine safeguards</p>
    </div>

    <!-- Metrics Grid -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px;">
      
      <div style="background: rgba(74, 158, 255, 0.1); border: 1px solid rgba(74, 158, 255, 0.3); border-radius: 12px; padding: 20px;">
        <div style="font-size: 0.85em; color: #a0a0a0; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">Forge Calls (24h)</div>
        <div id="aegis-forge-calls" style="font-size: 2.5em; font-weight: bold; color: #4a9eff;">-</div>
        <div style="font-size: 0.8em; color: #707080;">Total executions</div>
      </div>

      <div style="background: rgba(74, 158, 255, 0.1); border: 1px solid rgba(74, 158, 255, 0.3); border-radius: 12px; padding: 20px;">
        <div style="font-size: 0.85em; color: #a0a0a0; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">Valid Cycles</div>
        <div id="aegis-valid-calls" style="font-size: 2.5em; font-weight: bold; color: #10b981;">-</div>
        <div style="font-size: 0.8em; color: #707080;"><span id="aegis-valid-rate">-</span>% success</div>
      </div>

      <div style="background: rgba(74, 158, 255, 0.1); border: 1px solid rgba(74, 158, 255, 0.3); border-radius: 12px; padding: 20px;">
        <div style="font-size: 0.85em; color: #a0a0a0; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">Rejection Rate</div>
        <div id="aegis-rejection-rate" style="font-size: 2.5em; font-weight: bold; color: #ef4444;">-</div>
        <div style="font-size: 0.8em; color: #707080;"><span id="aegis-rejected-count">-</span> rejected</div>
      </div>

      <div style="background: rgba(74, 158, 255, 0.1); border: 1px solid rgba(74, 158, 255, 0.3); border-radius: 12px; padding: 20px;">
        <div style="font-size: 0.85em; color: #a0a0a0; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">Layer 5 Healings</div>
        <div id="aegis-healing-count" style="font-size: 2.5em; font-weight: bold; color: #a78bfa;">-</div>
        <div style="font-size: 0.8em; color: #707080;"><span id="aegis-healing-rate">-</span>% rate</div>
      </div>

      <div style="background: rgba(74, 158, 255, 0.1); border: 1px solid rgba(74, 158, 255, 0.3); border-radius: 12px; padding: 20px;">
        <div style="font-size: 0.85em; color: #a0a0a0; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">Avg Overlap</div>
        <div id="aegis-avg-overlap" style="font-size: 2.5em; font-weight: bold; color: #f59e0b;">-</div>
        <div style="font-size: 0.8em; color: #707080;">Layer 6 validation</div>
      </div>

      <div style="background: rgba(74, 158, 255, 0.1); border: 1px solid rgba(74, 158, 255, 0.3); border-radius: 12px; padding: 20px;">
        <div style="font-size: 0.85em; color: #a0a0a0; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;">Total Latency</div>
        <div id="aegis-total-latency" style="font-size: 2.5em; font-weight: bold; color: #06b6d4;">-</div>
        <div style="font-size: 0.8em; color: #707080;">Average per cycle</div>
      </div>

    </div>

    <!-- Recent Healing Events -->
    <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; margin-bottom: 30px;">
      <h3 style="font-size: 1.3em; margin-bottom: 20px; color: #4a9eff; border-bottom: 2px solid rgba(74, 158, 255, 0.3); padding-bottom: 10px;">✨ Recent Healing Events</h3>
      <div id="aegis-healing-log" style="max-height: 400px; overflow-y: auto;">
        <p style="color: #a0a0a0; text-align: center;">Loading...</p>
      </div>
    </div>

    <!-- Recent Executions -->
    <div style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px;">
      <h3 style="font-size: 1.3em; margin-bottom: 20px; color: #4a9eff; border-bottom: 2px solid rgba(74, 158, 255, 0.3); padding-bottom: 10px;">📊 Recent Forge Executions</h3>
      <div id="aegis-recent-events" style="max-height: 400px; overflow-y: auto;">
        <p style="color: #a0a0a0; text-align: center;">Loading...</p>
      </div>
    </div>

    <!-- Updated timestamp -->
    <div style="text-align: center; margin-top: 20px; padding: 20px; color: #707080; font-size: 0.9em;">
      Last updated: <span id="aegis-last-update">-</span>
    </div>

  </div>
</div>

<style>
  /* AEGIS Table Styles */
  .aegis-table {
    width: 100%;
    border-collapse: collapse;
    background: rgba(255, 255, 255, 0.02);
  }
  
  .aegis-table thead {
    background: rgba(74, 158, 255, 0.1);
  }
  
  .aegis-table th {
    text-align: left;
    padding: 12px;
    color: #4a9eff;
    font-weight: 600;
    border-bottom: 1px solid rgba(74, 158, 255, 0.2);
  }
  
  .aegis-table td {
    padding: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  
  .aegis-table tr:hover {
    background: rgba(74, 158, 255, 0.05);
  }
  
  .aegis-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8em;
    font-weight: 600;
  }
  
  .aegis-badge-success {
    background: rgba(16, 185, 129, 0.2);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.5);
  }
  
  .aegis-badge-failed {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.5);
  }
  
  .aegis-badge-healing {
    background: rgba(167, 139, 250, 0.2);
    color: #a78bfa;
    border: 1px solid rgba(167, 139, 250, 0.5);
  }
</style>

<script>
  const AEGIS_STATS_POLL = 5000;   // 5 seconds
  const AEGIS_EVENTS_POLL = 10000; // 10 seconds

  async function loadAegisStats() {
    try {
      const response = await fetch('/api/aegis/stats?hours=24');
      const stats = await response.json();
      
      document.getElementById('aegis-forge-calls').textContent = stats.total_forge_calls || 0;
      document.getElementById('aegis-valid-calls').textContent = stats.valid_calls || 0;
      document.getElementById('aegis-valid-rate').textContent = Math.round(100 - (stats.rejection_rate || 0));
      document.getElementById('aegis-rejection-rate').textContent = ((stats.rejection_rate || 0).toFixed(1)) + '%';
      document.getElementById('aegis-rejected-count').textContent = stats.invalid_calls || 0;
      document.getElementById('aegis-healing-count').textContent = stats.layer5_healing_applied || 0;
      document.getElementById('aegis-healing-rate').textContent = Math.round(stats.healing_rate || 0);
      document.getElementById('aegis-avg-overlap').textContent = ((stats.avg_overlap_percentage || 0).toFixed(1)) + '%';
      document.getElementById('aegis-total-latency').textContent = ((stats.avg_timings?.total_ms || 0).toFixed(0)) + 'ms';
      document.getElementById('aegis-last-update').textContent = new Date().toLocaleTimeString();
    } catch (error) {
      console.error('Failed to load AEGIS stats:', error);
    }
  }

  async function loadAegisHealingLog() {
    try {
      const response = await fetch('/api/aegis/healing-log?limit=15');
      const data = await response.json();
      
      let html = '<table class="aegis-table" style="width: 100%;"><thead><tr>';
      html += '<th>Time</th><th>Concept</th><th>Action</th><th>Magnitude</th><th>Reason</th>';
      html += '</tr></thead><tbody>';
      
      data.healing_events.forEach(event => {
        html += '<tr>';
        html += '<td style="font-size: 0.85em; color: #a0a0a0;">' + event.timestamp + '</td>';
        html += '<td>' + event.concept.substring(0, 40) + '</td>';
        html += '<td><span class="aegis-badge aegis-badge-healing">' + event.action + '</span></td>';
        html += '<td style="font-size: 0.85em;">' + event.magnitude.toFixed(3) + '</td>';
        html += '<td style="font-size: 0.85em; color: #a0a0a0;">' + event.reason.substring(0, 50) + '</td>';
        html += '</tr>';
      });
      
      html += '</tbody></table>';
      if (data.healing_events.length === 0) {
        html = '<p style="text-align: center; color: #a0a0a0;">No healing events in the last 24 hours</p>';
      }
      document.getElementById('aegis-healing-log').innerHTML = html;
    } catch (error) {
      console.error('Failed to load healing log:', error);
    }
  }

  async function loadAegisRecentEvents() {
    try {
      const response = await fetch('/api/aegis/recent-events?limit=15');
      const data = await response.json();
      
      let html = '<table class="aegis-table" style="width: 100%;"><thead><tr>';
      html += '<th>Time</th><th>Concept</th><th>Healing</th><th>Overlap</th><th>Status</th>';
      html += '</tr></thead><tbody>';
      
      data.events.forEach(event => {
        const time = new Date(event.timestamp * 1000).toLocaleTimeString();
        const healingBadge = event.healing_action && event.healing_action !== 'none' ?
          '<span class="aegis-badge aegis-badge-healing">' + event.healing_action + '</span>' : '-';
        const statusBadge = event.valid ?
          '<span class="aegis-badge aegis-badge-success">✓ Valid</span>' :
          '<span class="aegis-badge aegis-badge-failed">✗ Failed</span>';
        
        html += '<tr>';
        html += '<td style="font-size: 0.85em; color: #a0a0a0;">' + time + '</td>';
        html += '<td>' + event.concept.substring(0, 40) + '</td>';
        html += '<td>' + healingBadge + '</td>';
        html += '<td style="text-align: right;">' + (event.overlap_percentage || 0).toFixed(1) + '%</td>';
        html += '<td>' + statusBadge + '</td>';
        html += '</tr>';
      });
      
      html += '</tbody></table>';
      if (data.events.length === 0) {
        html = '<p style="text-align: center; color: #a0a0a0;">No forge executions yet</p>';
      }
      document.getElementById('aegis-recent-events').innerHTML = html;
    } catch (error) {
      console.error('Failed to load recent events:', error);
    }
  }

  // Initial load and periodic updates
  loadAegisStats();
  loadAegisHealingLog();
  loadAegisRecentEvents();
  
  setInterval(loadAegisStats, AEGIS_STATS_POLL);
  setInterval(loadAegisHealingLog, AEGIS_EVENTS_POLL);
  setInterval(loadAegisRecentEvents, AEGIS_EVENTS_POLL);

  // Make tab accessible from global scope
  window.showAegisMetrics = function() {
    const tab = document.getElementById('aegis-metrics-tab');
    if (tab) {
      tab.style.display = 'block';
      // Hide other tabs (if they exist)
      const allTabs = document.querySelectorAll('[id$="-tab"]');
      allTabs.forEach(t => {
        if (t.id !== 'aegis-metrics-tab') {
          t.style.display = 'none';
        }
      });
    }
  };
</script>
"""


def inject_aegis_dashboard_into_html(html_path):
    """
    Inject the AEGIS dashboard component into an existing HTML file.
    
    Usage:
        inject_aegis_dashboard_into_html('inference/static/index.html')
    """
    from pathlib import Path
    
    html_file = Path(html_path)
    if not html_file.exists():
        print(f"HTML file not found: {html_path}")
        return False
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already injected
    if 'aegis-metrics-tab' in content:
        print(f"AEGIS dashboard already injected in {html_path}")
        return True
    
    # Find a good place to insert (before closing body tag)
    insert_pos = content.find('</body>')
    if insert_pos == -1:
        # No closing body tag, append to end
        insert_pos = len(content)
    
    # Insert the component
    modified_content = (
        content[:insert_pos] +
        '\n' + AEGIS_DASHBOARD_COMPONENT + '\n' +
        content[insert_pos:]
    )
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(modified_content)
    
    print(f"✓ AEGIS dashboard injected into {html_path}")
    return True


if __name__ == "__main__":
    print("\n" + "="*70)
    print("AEGIS Dashboard Component for Codette Web UI")
    print("="*70)
    print("\nUsage:")
    print("  1. In your HTML template, add this before </body>:")
    print("    ", AEGIS_DASHBOARD_COMPONENT[:100] + "...")
    print("\n  2. Or use the injection function:")
    print("    from aegis_metrics_ui import inject_aegis_dashboard_into_html")
    print("    inject_aegis_dashboard_into_html('path/to/index.html')\n")
