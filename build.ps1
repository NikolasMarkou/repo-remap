#Requires -Version 7
# build.ps1 - PowerShell build script for Repo Remap Claude Skill
# Usage: .\build.ps1 [command]
# Commands: build, build-combined, package, package-combined, package-tar, validate, lint, test, clean, list, sync-skill, help
#
# PowerShell 7+ is REQUIRED, and every Get-Content/Set-Content below names -Encoding utf8
# explicitly. Under Windows PowerShell 5.1 both default to the ANSI codepage, so the
# read-modify-write of SKILL.md would corrupt non-ASCII glyphs. The Makefile channel is
# byte-clean (cp + sed), so this is the one channel that needs the guard. Do NOT drop -Encoding.
#
# Keep in lockstep with the Makefile: src/scripts/test_build_channels.py pins the target list,
# the validate gate set, the lint list, the test command and the combined-file Note.

param(
    [Parameter(Position=0)]
    [string]$Command = "package"
)

$SkillName = "repo-remap"
$Version = (Get-Content "$PSScriptRoot/VERSION" -Raw -Encoding utf8).Trim()
$BuildDir = "build"
$DistDir = "dist"
$Python = if ($env:PYTHON) { $env:PYTHON } else { "python3" }

$SkillFile = "src/SKILL.md"
# Explicit on purpose: check_*.py gates and test_*.py suites are dev-only and never ship.
$ScriptFiles = @("src/scripts/module_tree.py")
$DocFiles = @("README.md", "LICENSE", "CHANGELOG.md", "VERSION")
$LintFiles = @(
    "src/scripts/check_agent_wiring.py",
    "src/scripts/check_changelog_parity.py",
    "src/scripts/check_ignore_parity.py",
    "src/scripts/check_readme_parity.py",
    "src/scripts/check_test_count.py",
    "src/scripts/module_tree.py",
    "src/scripts/test_build_channels.py",
    "src/scripts/test_check_agent_wiring.py",
    "src/scripts/test_check_changelog_parity.py",
    "src/scripts/test_check_ignore_parity.py",
    "src/scripts/test_check_readme_parity.py",
    "src/scripts/test_check_test_count.py",
    "src/scripts/test_module_tree.py"
)

function Show-Help {
    Write-Host "Repo Remap Skill - Build Script" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\build.ps1 [command]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  build            - Build skill package (SKILL.md, scripts/, agents/, references/)"
    Write-Host "  build-combined   - Build single-file skill (SKILL.md + inlined references and agents)"
    Write-Host "  package          - Create zip package"
    Write-Host "  package-combined - Create single-file skill in dist/"
    Write-Host "  package-tar      - Create tarball package"
    Write-Host "  validate         - Validate skill structure and parity gates"
    Write-Host "  lint             - Check script syntax"
    Write-Host "  test             - Run tests and the TEST_COUNT gate"
    Write-Host "  clean            - Remove build artifacts"
    Write-Host "  list             - Show package contents"
    Write-Host "  sync-skill       - Opt-in: deploy skill (with agents/) to ~/.claude/skills, rr-* agents also to ~/.claude/agents"
    Write-Host "  help             - Show this help"
    Write-Host ""
    Write-Host "Skill: $SkillName v$Version"
}

function Substitute-Placeholders {
    param([string]$Path)
    $date = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd")
    $commit = (git rev-parse --short HEAD).Trim()
    $content = Get-Content $Path -Raw -Encoding utf8
    $content = $content -replace "__SKILL_VERSION__", $Version
    $content = $content -replace "__SKILL_DATE__", $date
    $content = $content -replace "__SKILL_COMMIT__", $commit
    Set-Content -Path $Path -Value $content -Encoding utf8 -NoNewline
}

# src/agents/ and src/references/ also hold this repo's own per-module README.md and CLAUDE.md.
# Those are repo docs, not skill content: agents are rr-*.md only, references exclude both docs.
# Keep in lockstep with the Makefile's AGENT_FILES and REFERENCE_FILES.
function Get-ReferenceFiles {
    # Leading comma: return the array as one object so an empty or one-item set stays an array.
    return ,@(Get-ChildItem src/references -Filter *.md -File | Where-Object { $_.Name -notin @('README.md','CLAUDE.md') } | Sort-Object Name)
}

function Get-AgentFiles {
    return ,@(Get-ChildItem src/agents -Filter rr-*.md -File | Sort-Object Name)
}

function Invoke-Build {
    Write-Host "Building skill package: $SkillName"
    $target = Join-Path $BuildDir $SkillName
    foreach ($d in @("scripts", "agents", "references")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $target $d) | Out-Null
    }
    Copy-Item $SkillFile (Join-Path $target "SKILL.md") -Force
    Substitute-Placeholders (Join-Path $target "SKILL.md")
    foreach ($f in $ScriptFiles) { Copy-Item $f (Join-Path $target "scripts") -Force }
    foreach ($f in (Get-AgentFiles)) { Copy-Item $f.FullName (Join-Path $target "agents") -Force }
    foreach ($f in (Get-ReferenceFiles)) { Copy-Item $f.FullName (Join-Path $target "references") -Force }
    foreach ($f in $DocFiles) { Copy-Item $f $target -Force }
    Write-Host "Build complete: $target"
}

function Invoke-BuildCombined {
    Write-Host "Building combined single-file skill..."
    New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
    $out = Join-Path $BuildDir "$SkillName-combined.md"
    Copy-Item $SkillFile $out -Force
    # The Note sits at the END because SKILL.md's YAML frontmatter must remain the file's
    # first bytes. Keep byte-identical to the Makefile's note: test_build_channels.py pins the pair.
    $note = @(
        "> **Note**: This combined file is a PASTE-INTO-CONTEXT artifact, not an installed skill.",
        "> It ships no scripts and no installed agents, so ``python3 <skill-path>/scripts/module_tree.py``",
        "> is not runnable as written. Use the manual mapping fallback in Step 0 instead: list directories,",
        "> count direct files, discard ignored paths, sort by path depth descending. The references and agent",
        "> definitions are inlined above, so run the passes in-thread, or spawn general-purpose subagents",
        "> told to follow the inlined rr-* section for their role. The zip or tarball package includes",
        "> the script and the agent definitions."
    )
    $body = Get-Content $out -Raw -Encoding utf8
    # Each inlined file: blank line, ---, blank line, <!-- file: <dir>/<name> -->, blank line, body.
    # Keep order (references, then agents) and framing byte-identical to the Makefile's build-combined.
    $groups = @(
        @("references", "src/references/*.md", (Get-ReferenceFiles)),
        @("agents", "src/agents/rr-*.md", (Get-AgentFiles)))
    foreach ($g in $groups) {
        $parts = @($g[2])
        if ($parts.Count -eq 0) { Write-Host "ERROR: no files match $($g[1])" -ForegroundColor Red; exit 1 }
        foreach ($p in $parts) {
            $rel = "$($g[0])/$($p.Name)"
            $text = Get-Content $p.FullName -Raw -Encoding utf8
            $body += "`n---`n`n<!-- file: $rel -->`n`n" + $text
        }
    }
    $body += "`n---`n`n" + ($note -join "`n") + "`n"
    Set-Content -Path $out -Value $body -Encoding utf8 -NoNewline
    Substitute-Placeholders $out
    Write-Host "Combined skill created: $out"
}

function Invoke-Package {
    Invoke-Validate
    Invoke-Build
    Write-Host "Packaging skill as zip..."
    New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
    $zip = Join-Path $DistDir "$SkillName-v$Version.zip"
    if (Test-Path $zip) { Remove-Item $zip -Force }
    Compress-Archive -Path (Join-Path $BuildDir $SkillName) -DestinationPath $zip
    Write-Host "Package created: $zip"
}

function Invoke-PackageCombined {
    Invoke-Validate
    Invoke-BuildCombined
    New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
    Copy-Item (Join-Path $BuildDir "$SkillName-combined.md") $DistDir -Force
    Write-Host "Combined skill copied to: $DistDir/$SkillName-combined.md"
}

function Invoke-PackageTar {
    Invoke-Validate
    Invoke-Build
    Write-Host "Packaging skill as tarball..."
    New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
    $tar = Join-Path $DistDir "$SkillName-v$Version.tar.gz"
    tar -czf $tar -C $BuildDir $SkillName
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: tar failed" -ForegroundColor Red; exit 1 }
    Write-Host "Package created: $tar"
}

function Invoke-Validate {
    Write-Host "Validating skill structure..."
    $errors = @()
    # A missing script or gate is an error, never a skip: the Makefile dies when one is gone,
    # so a Test-Path wrapper here would make a deleted gate pass validation on Windows only.
    if (-not (Test-Path $SkillFile)) { $errors += "$SkillFile not found" }
    else {
        $skill = Get-Content $SkillFile -Raw -Encoding utf8
        if ($skill -notmatch "(?m)^name:") { $errors += "SKILL.md missing 'name' in frontmatter" }
        if ($skill -notmatch "(?m)^description:") { $errors += "SKILL.md missing 'description' in frontmatter" }
        Write-Host "Checking version placeholders..."
        foreach ($tok in @("__SKILL_VERSION__", "__SKILL_DATE__", "__SKILL_COMMIT__")) {
            if ($skill -notlike "*$tok*") { $errors += "$SkillFile missing placeholder $tok" }
        }
        Write-Host "Checking script citations..."
        $refs = [regex]::Matches($skill, "scripts/[a-z0-9_]+\.py") | ForEach-Object { $_.Value } | Sort-Object -Unique
        foreach ($ref in $refs) {
            if (-not (Test-Path "src/$ref")) { $errors += "$SkillFile cites $ref but src/$ref not found" }
        }
        # Every references/<x>.md and agents/rr-<x>.md cited in SKILL.md must exist under src/
        Write-Host "Checking reference citations..."
        $refs = [regex]::Matches($skill, "references/[a-z0-9_-]+\.md") | ForEach-Object { $_.Value } | Sort-Object -Unique
        foreach ($ref in $refs) {
            if (-not (Test-Path "src/$ref")) { $errors += "$SkillFile cites $ref but src/$ref not found" }
        }
        Write-Host "Checking agent citations..."
        $refs = [regex]::Matches($skill, "agents/rr-[a-z-]+\.md") | ForEach-Object { $_.Value } | Sort-Object -Unique
        foreach ($ref in $refs) {
            if (-not (Test-Path "src/$ref")) { $errors += "$SkillFile cites $ref but src/$ref not found" }
        }
    }
    if (-not (Test-Path "src/scripts")) { $errors += "src/scripts/ directory not found" }
    if (-not (Test-Path "src/references")) { $errors += "src/references/ directory not found" }
    if (-not (Test-Path "src/agents")) { $errors += "src/agents/ directory not found" }
    else {
        Write-Host "Checking agent frontmatter..."
        $agents = Get-AgentFiles
        if ($agents.Count -eq 0) { $errors += "src/agents/ has no agent definitions" }
        foreach ($a in $agents) {
            $agentText = Get-Content $a.FullName -Raw -Encoding utf8
            foreach ($key in @("name", "description", "tools")) {
                if ($agentText -notmatch "(?m)^${key}:") { $errors += "src/agents/$($a.Name) missing '$key' in frontmatter" }
            }
        }
    }
    Write-Host "Checking README badge parity (version + test count)..."
    & $Python src/scripts/check_readme_parity.py
    if ($LASTEXITCODE -ne 0) { $errors += "check_readme_parity.py failed" }
    Write-Host "Checking CHANGELOG parity (top entry <-> VERSION)..."
    & $Python src/scripts/check_changelog_parity.py
    if ($LASTEXITCODE -ne 0) { $errors += "check_changelog_parity.py failed" }
    Write-Host "Checking ignore-list parity (README <-> module_tree.py)..."
    & $Python src/scripts/check_ignore_parity.py
    if ($LASTEXITCODE -ne 0) { $errors += "check_ignore_parity.py failed" }
    Write-Host "Checking agent wiring (SKILL.md <-> agents/ <-> references/)..."
    & $Python src/scripts/check_agent_wiring.py
    if ($LASTEXITCODE -ne 0) { $errors += "check_agent_wiring.py failed" }
    if ($errors.Count -gt 0) {
        foreach ($e in $errors) { Write-Host "ERROR: $e" -ForegroundColor Red }
        exit 1
    }
    Write-Host "Validation passed!" -ForegroundColor Green
}

function Invoke-Lint {
    Write-Host "Checking script syntax..."
    foreach ($f in $LintFiles) {
        & $Python -m py_compile $f
        if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: syntax check failed for $f" -ForegroundColor Red; exit 1 }
    }
    Write-Host "Syntax check passed!" -ForegroundColor Green
}

function Invoke-Test {
    Invoke-Lint
    Write-Host "Running test suite..."
    & $Python -m unittest discover -s src/scripts -p "test_*.py"
    if ($LASTEXITCODE -ne 0) { Write-Host "ERROR: tests failed" -ForegroundColor Red; exit 1 }
    Write-Host "Checking TEST_COUNT against the live suite result..."
    & $Python src/scripts/check_test_count.py
    if ($LASTEXITCODE -ne 0) { exit 1 }
    Write-Host "Tests passed!" -ForegroundColor Green
}

function Invoke-Clean {
    Write-Host "Cleaning build artifacts..."
    foreach ($d in @($BuildDir, $DistDir, "src/scripts/__pycache__")) {
        if (Test-Path $d) { Remove-Item $d -Recurse -Force }
    }
    Write-Host "Clean complete"
}

function Invoke-List {
    Invoke-Build
    Write-Host "Package contents:"
    Get-ChildItem -Path (Join-Path $BuildDir $SkillName) -Recurse -File | ForEach-Object { $_.FullName } | Sort-Object
}

function Invoke-SyncSkill {
    $install = Join-Path $HOME ".claude/skills/$SkillName"
    # Shared user-level agents dir: prune and compare ONLY rr-*.md there, never other agents.
    $agentInstall = Join-Path $HOME ".claude/agents"
    # Skill-owned agents dir: SKILL.md reads <skill-path>/agents/rr-*.md, so rr-*.md goes to both.
    $skillAgents = Join-Path $install "agents"
    Write-Host "Syncing repo source to local installed skill: $install"
    foreach ($d in @((Join-Path $install "scripts"), (Join-Path $install "references"), $skillAgents, $agentInstall)) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
    }
    # Prune before copy: a copy-only sync leaves repo-deleted files behind forever.
    Get-ChildItem (Join-Path $install "scripts") -Filter "*.py" -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem (Join-Path $install "references") -Filter "*.md" -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem $skillAgents -Filter "*.md" -ErrorAction SilentlyContinue | Remove-Item -Force
    Get-ChildItem $agentInstall -Filter "rr-*.md" -ErrorAction SilentlyContinue | Remove-Item -Force
    Copy-Item $SkillFile (Join-Path $install "SKILL.md") -Force
    foreach ($f in $ScriptFiles) { Copy-Item $f (Join-Path $install "scripts") -Force }
    foreach ($f in (Get-ReferenceFiles)) { Copy-Item $f.FullName (Join-Path $install "references") -Force }
    foreach ($f in (Get-AgentFiles)) { Copy-Item $f.FullName $skillAgents -Force }
    foreach ($f in (Get-AgentFiles)) { Copy-Item $f.FullName $agentInstall -Force }
    foreach ($f in $DocFiles) { Copy-Item $f $install -Force }
    $leaked = Get-ChildItem (Join-Path $install "scripts") -Include "test_*.py", "check_*.py" -Recurse
    if ($leaked) { Write-Host "ERROR: sync-skill shipped dev-only scripts into the install" -ForegroundColor Red; exit 1 }
    $pairs = @(
        @($SkillFile, (Join-Path $install "SKILL.md")),
        @("src/scripts/module_tree.py", (Join-Path $install "scripts/module_tree.py")),
        @("VERSION", (Join-Path $install "VERSION")))
    # references/: the installed file set must equal Get-ReferenceFiles (no extra name, none
    # missing), then each file is compared. src/references/ README.md and CLAUDE.md never ship.
    $srcRefs = @(foreach ($f in (Get-ReferenceFiles)) { $f.Name } | Sort-Object)
    $dstRefs = @(Get-ChildItem (Join-Path $install "references") -File | ForEach-Object { $_.Name } | Sort-Object)
    if (($srcRefs -join "|") -ne ($dstRefs -join "|")) { Write-Host "ERROR: sync diff mismatch: references/" -ForegroundColor Red; exit 1 }
    foreach ($n in $srcRefs) { $pairs += ,@("src/references/$n", (Join-Path $install "references/$n")) }
    # Skill agents/: the installed file set must equal Get-AgentFiles, then each file is compared.
    $srcAgents = @(foreach ($f in (Get-AgentFiles)) { $f.Name } | Sort-Object)
    $dstAgents = @(Get-ChildItem $skillAgents -File | ForEach-Object { $_.Name } | Sort-Object)
    if (($srcAgents -join "|") -ne ($dstAgents -join "|")) { Write-Host "ERROR: sync diff mismatch: agents/" -ForegroundColor Red; exit 1 }
    foreach ($agentFile in (Get-AgentFiles)) {
        $pairs += ,@("src/agents/$($agentFile.Name)", (Join-Path $skillAgents $agentFile.Name))
        $pairs += ,@("src/agents/$($agentFile.Name)", (Join-Path $agentInstall $agentFile.Name))
    }
    foreach ($pair in $pairs) {
        if (-not (Test-Path $pair[1])) { Write-Host "ERROR: sync diff mismatch: $($pair[0])" -ForegroundColor Red; exit 1 }
        $a = Get-Content $pair[0] -Raw -Encoding utf8
        $b = Get-Content $pair[1] -Raw -Encoding utf8
        if ($a -ne $b) { Write-Host "ERROR: sync diff mismatch: $($pair[0])" -ForegroundColor Red; exit 1 }
    }
    Write-Host "Sync verified (SKILL.md, module_tree.py, VERSION, references/, agents/ in skill and ~/.claude/agents/rr-*.md)." -ForegroundColor Green
}

switch ($Command.ToLower()) {
    "build"            { Invoke-Build }
    "build-combined"   { Invoke-BuildCombined }
    "package"          { Invoke-Package }
    "package-combined" { Invoke-PackageCombined }
    "package-tar"      { Invoke-PackageTar }
    "validate"         { Invoke-Validate }
    "lint"             { Invoke-Lint }
    "test"             { Invoke-Test }
    "clean"            { Invoke-Clean }
    "list"             { Invoke-List }
    "sync-skill"       { Invoke-SyncSkill }
    "help"             { Show-Help }
    default            { Write-Host "Unknown command: $Command" -ForegroundColor Red; Show-Help; exit 1 }
}
