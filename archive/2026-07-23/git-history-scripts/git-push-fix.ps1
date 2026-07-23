# CODETTE GIT CLEANUP AND PUSH SCRIPT
# Purpose: Remove results.zip from git history and force push to GitHub
# Usage: Run in PowerShell as Administrator (recommended)

param(
    [switch]$Force = $false,
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

# ====================================================================
# SECTION 1: ENVIRONMENT SETUP
# ====================================================================
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  CODETTE GIT CLEANUP & PUSH SCRIPT                         ║" -ForegroundColor Cyan
Write-Host "║  Removing results.zip from history + Force Push            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$repoPath = "j:\codette-clean"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-Host "[$timestamp] Repository: $repoPath" -ForegroundColor Yellow
Write-Host "[$timestamp] Working directory: $(Get-Location)" -ForegroundColor Yellow
Write-Host ""

# ====================================================================
# SECTION 2: PROCESS CLEANUP
# ====================================================================
Write-Host "[STEP 1] Killing any stuck git processes..." -ForegroundColor Magenta

try {
    $gitProcesses = Get-Process -Name git -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -eq 'git' }
    if ($gitProcesses) {
        Write-Host "  Found $(($gitProcesses | Measure-Object).Count) git process(es)" -ForegroundColor Yellow
        $gitProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
        Write-Host "  ✓ Git processes stopped" -ForegroundColor Green
    } else {
        Write-Host "  ✓ No stuck git processes" -ForegroundColor Green
    }
}
catch {
    Write-Host "  ✗ Error stopping processes: $_" -ForegroundColor Red
}

Write-Host ""

# ====================================================================
# SECTION 3: CLEANUP BACKUP DIRECTORIES
# ====================================================================
Write-Host "[STEP 2] Cleaning filter-branch backup directories..." -ForegroundColor Magenta

$backupPaths = @(
    "$repoPath\.git-rewrite",
    "$repoPath\.git\refs\original"
)

foreach ($path in $backupPaths) {
    if (Test-Path $path) {
        Write-Host "  Removing: $path" -ForegroundColor Yellow
        try {
            Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Host "  ✓ Removed" -ForegroundColor Green
        }
        catch {
            Write-Host "  ✗ Error: $_" -ForegroundColor Red
        }
    }
}

Write-Host ""

# ====================================================================
# SECTION 4: VERIFY CURRENT STATE
# ====================================================================
Write-Host "[STEP 3] Checking current git state..." -ForegroundColor Magenta

cd $repoPath

# Check if results.zip is in the repository
Write-Host "  Scanning for results.zip in git history..." -ForegroundColor Yellow
$hasFile = $false

try {
    $output = & git log --all --full-history --diff-filter=D -- results.zip 2>&1
    if ($LASTEXITCODE -eq 0 -and $output) {
        Write-Host "  ✓ Found deletion record of results.zip" -ForegroundColor Green
    }
    
    # More aggressive check
    $treeCheck = & git log --all --full-history -- results.zip 2>&1
    if ($treeCheck -match "results.zip" -and -not ($treeCheck -match "chore: remove")) {
        $hasFile = $true
        Write-Host "  ✗ results.zip still in history!" -ForegroundColor Red
    }
    else {
        Write-Host "  ✓ results.zip appears to be removed from history" -ForegroundColor Green
    }
}
catch {
    Write-Host "  ⚠ Error checking history: $_" -ForegroundColor Yellow
    $hasFile = $true
}

Write-Host ""

# ====================================================================
# SECTION 5: AGGRESSIVE CLEANUP IF NEEDED
# ====================================================================
if ($hasFile) {
    Write-Host "[STEP 4] AGGRESSIVE CLEANUP - Removing results.zip from all commits..." -ForegroundColor Magenta
    
    try {
        Write-Host "  Running: git filter-branch --force --index-filter..." -ForegroundColor Yellow
        
        $env:FILTER_BRANCH_SQUELCH_WARNING = 1
        
        $filterCmd = @"
`$FILTER_BRANCH_SQUELCH_WARNING = 1
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch results.zip' --prune-empty -- --all 2>&1
"@
        
        $output = & powershell -NoProfile -Command $filterCmd
        
        if ($LASTEXITCODE -eq 0 -or $output -match "Rewrite\|Finished\|nothing to rewrite") {
            Write-Host "  ✓ Filter-branch completed" -ForegroundColor Green
            if ($Verbose) {
                Write-Host "  Output: $(($output | Select-Object -Last 5) -join '; ')" -ForegroundColor Gray
            }
        }
        else {
            Write-Host "  ⚠ Filter-branch finished with status: $LASTEXITCODE" -ForegroundColor Yellow
            if ($Verbose) {
                Write-Host "  Output: $($output -join '; ')" -ForegroundColor Gray
            }
        }
    }
    catch {
        Write-Host "  ✗ Error during filter-branch: $_" -ForegroundColor Red
    }
    
    Write-Host ""
}

# ====================================================================
# SECTION 6: REFLOG & GARBAGE COLLECTION
# ====================================================================
Write-Host "[STEP 5] Running garbage collection and reflog cleanup..." -ForegroundColor Magenta

try {
    Write-Host "  Expiring reflog..." -ForegroundColor Yellow
    & git reflog expire --expire=now --all 2>&1 | Out-Null
    Write-Host "  ✓ Reflog expired" -ForegroundColor Green
}
catch {
    Write-Host "  ✗ Reflog error: $_" -ForegroundColor Red
}

try {
    Write-Host "  Running aggressive garbage collection..." -ForegroundColor Yellow
    & git gc --prune=now --aggressive 2>&1 | Out-Null
    Write-Host "  ✓ GC completed" -ForegroundColor Green
}
catch {
    Write-Host "  ✗ GC error: $_" -ForegroundColor Red
}

Write-Host ""

# ====================================================================
# SECTION 7: VERIFY CLEANUP
# ====================================================================
Write-Host "[STEP 6] Verifying cleanup..." -ForegroundColor Magenta

try {
    $checkOutput = & git log --all --full-history -- results.zip 2>&1
    if ($checkOutput -match "f03e8f8" -or ($checkOutput -match "results.zip" -and -not ($checkOutput -match "chore: remove"))) {
        Write-Host "  ✗ WARNING: results.zip may still be in history!" -ForegroundColor Red
        Write-Host "  This might cause push to fail." -ForegroundColor Red
    }
    else {
        Write-Host "  ✓ results.zip successfully removed from history" -ForegroundColor Green
    }
}
catch {
    Write-Host "  ⚠ Could not verify: $_" -ForegroundColor Yellow
}

Write-Host ""

# ====================================================================
# SECTION 8: PUSH TO GITHUB
# ====================================================================
Write-Host "[STEP 7] Pushing to GitHub..." -ForegroundColor Magenta

Write-Host "  Command: git push origin main --force --verbose" -ForegroundColor Yellow
Write-Host "  (This may take 1-2 minutes...)" -ForegroundColor Gray
Write-Host ""

try {
    $pushStart = Get-Date
    
    # Capture all output
    $pushOutput = & git push origin main --force --verbose 2>&1
    
    $pushEnd = Get-Date
    $pushDuration = ($pushEnd - $pushStart).TotalSeconds
    
    # Check for success indicators
    $isSuccess = $false
    if ($LASTEXITCODE -eq 0) {
        $isSuccess = $true
    }
    elseif ($pushOutput -match "Total.*done\|Resolving deltas.*completed" -and $pushOutput -notmatch "rejected\|error") {
        $isSuccess = $true
    }
    
    if ($isSuccess) {
        Write-Host "  ✓ PUSH SUCCESSFUL! (${pushDuration}s)" -ForegroundColor Green
        Write-Host ""
        Write-Host "  Push output (last 10 lines):" -ForegroundColor Yellow
        $pushOutput | Select-Object -Last 10 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    }
    else {
        Write-Host "  ✗ PUSH FAILED (${pushDuration}s)" -ForegroundColor Red
        Write-Host ""
        Write-Host "  Error output:" -ForegroundColor Red
        $pushOutput | Where-Object { $_ -match "error|rejected|failed" } | ForEach-Object { Write-Host "    $_" -ForegroundColor Red }
        
        # Show all output if verbose
        if ($Verbose) {
            Write-Host ""
            Write-Host "  Full output:" -ForegroundColor Yellow
            $pushOutput | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        }
    }
}
catch {
    Write-Host "  ✗ Exception during push: $_" -ForegroundColor Red
}

Write-Host ""

# ====================================================================
# SECTION 9: VERIFY FINAL STATE
# ====================================================================
Write-Host "[STEP 8] Verifying final git state..." -ForegroundColor Magenta

try {
    $status = & git status -sb 2>&1
    Write-Host "  Status:" -ForegroundColor Yellow
    $status | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
    
    if ($status -match "main.*origin/main.*\[ahead" -or $status -match "have diverged") {
        Write-Host ""
        Write-Host "  Fetching from remote..." -ForegroundColor Yellow
        & git fetch origin 2>&1 | Out-Null
        
        $status2 = & git status -sb 2>&1
        Write-Host "  Updated status:" -ForegroundColor Yellow
        $status2 | ForEach-Object { Write-Host "    $_" -ForegroundColor Gray }
        
        if ($status2 -match "main.*origin/main" -and -not ($status2 -match "\[ahead")) {
            Write-Host ""
            Write-Host "  ✓ Repository is in sync with remote!" -ForegroundColor Green
        }
    }
    else {
        Write-Host ""
        Write-Host "  ✓ Repository status looks good" -ForegroundColor Green
    }
}
catch {
    Write-Host "  ✗ Error checking status: $_" -ForegroundColor Red
}

Write-Host ""

# ====================================================================
# SECTION 10: SUMMARY
# ====================================================================
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  CLEANUP COMPLETE                                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Check your GitHub repository: https://github.com/Raiff1982/Codette-Reasoning" -ForegroundColor Gray
Write-Host "  2. Verify main branch has the latest commits" -ForegroundColor Gray
Write-Host "  3. If still having issues, run with -Verbose flag for detailed output" -ForegroundColor Gray
Write-Host ""
Write-Host "If push failed:" -ForegroundColor Red
Write-Host "  • Check your GitHub authentication" -ForegroundColor Gray
Write-Host "  • Run: git credential-cache erase" -ForegroundColor Gray
Write-Host "  • Or use: gh auth login" -ForegroundColor Gray
Write-Host ""

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "[$timestamp] Script finished" -ForegroundColor Yellow
