<#
.SYNOPSIS
Installs the Spec Kit-generated Azure Interview skill into a custom Hermes home.

.DESCRIPTION
Spec Kit currently writes Hermes skills under the default user-profile location.
When HERMES_HOME points elsewhere, this adapter copies the generated SKILL.md
into the active categorized Hermes skill tree.

The operation is idempotent. Existing differing content is never overwritten
unless -Force is supplied. A backup is created before forced replacement.

.PARAMETER HermesHome
The active Hermes home. Defaults to the HERMES_HOME environment variable.

.PARAMETER SourceSkillPath
The Spec Kit-generated SKILL.md path. Defaults to the standard user-profile
location used by the Spec Kit Hermes integration.

.PARAMETER Category
The Hermes skill category. Defaults to devops.

.PARAMETER Force
Allows replacement when the target exists with different content.

.EXAMPLE
.\Install-HermesSkillAdapter.ps1

.EXAMPLE
.\Install-HermesSkillAdapter.ps1 -Category devops -Force
#>

[CmdletBinding(SupportsShouldProcess, ConfirmImpact = "Medium")]
param(
    [Parameter()]
    [string] $HermesHome = $env:HERMES_HOME,

    [Parameter()]
    [string] $SourceSkillPath,

    [Parameter()]
    [ValidatePattern("^[a-z0-9-]+$")]
    [string] $Category = "devops",

    [Parameter()]
    [switch] $Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$SkillName = "speckit-azure-interview-run"

if ([string]::IsNullOrWhiteSpace($HermesHome)) {
    throw @"
HERMES_HOME is not configured.

Set HERMES_HOME to the active Hermes profile before running this adapter.
Example:

`$env:HERMES_HOME = "E:\AI\Hermes"
"@
}

if (-not (Test-Path -LiteralPath $HermesHome -PathType Container)) {
    throw "Hermes home does not exist: $HermesHome"
}

if ([string]::IsNullOrWhiteSpace($SourceSkillPath)) {
    $UserProfile = $env:USERPROFILE

    if ([string]::IsNullOrWhiteSpace($UserProfile)) {
        throw "USERPROFILE is unavailable; specify -SourceSkillPath explicitly."
    }

    $SourceSkillPath = Join-Path `
        $UserProfile `
        ".hermes\skills\$SkillName\SKILL.md"
}

if (-not (Test-Path -LiteralPath $SourceSkillPath -PathType Leaf)) {
    throw @"
The Spec Kit-generated Hermes skill was not found:

$SourceSkillPath

Initialize a Spec Kit project with the Hermes integration and install the
azure-interview extension before running this adapter.
"@
}

$ResolvedHermesHome = (
    Resolve-Path -LiteralPath $HermesHome
).Path

$ResolvedSourceSkill = (
    Resolve-Path -LiteralPath $SourceSkillPath
).Path

$SourceContent = Get-Content `
    -LiteralPath $ResolvedSourceSkill `
    -Raw `
    -Encoding UTF8

$EscapedSkillName = [regex]::Escape($SkillName)
$ExpectedNamePattern = "(?m)^name:\s*$EscapedSkillName\s*$"

if ($SourceContent -notmatch $ExpectedNamePattern) {
    throw @"
The source file is not the expected generated skill.

Expected frontmatter name:
name: $SkillName

Source:
$ResolvedSourceSkill
"@
}

if ($SourceContent -notmatch "(?m)^---\s*$") {
    throw "The generated skill does not contain valid frontmatter delimiters."
}

$SkillsRoot = Join-Path $ResolvedHermesHome "skills"
$CategoryRoot = Join-Path $SkillsRoot $Category
$TargetDirectory = Join-Path $CategoryRoot $SkillName
$TargetSkillPath = Join-Path $TargetDirectory "SKILL.md"

$CanonicalSkillsRoot = [System.IO.Path]::GetFullPath(
    $SkillsRoot
).TrimEnd(
    [System.IO.Path]::DirectorySeparatorChar,
    [System.IO.Path]::AltDirectorySeparatorChar
)

$CanonicalTarget = [System.IO.Path]::GetFullPath($TargetSkillPath)

$RequiredPrefix = (
    $CanonicalSkillsRoot +
    [System.IO.Path]::DirectorySeparatorChar
)

if (-not $CanonicalTarget.StartsWith(
    $RequiredPrefix,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "Calculated target path escapes the Hermes skills root."
}

if (Test-Path -LiteralPath $TargetSkillPath -PathType Leaf) {
    $SourceHash = (
        Get-FileHash -LiteralPath $ResolvedSourceSkill -Algorithm SHA256
    ).Hash

    $TargetHash = (
        Get-FileHash -LiteralPath $TargetSkillPath -Algorithm SHA256
    ).Hash

    if ($SourceHash -eq $TargetHash) {
        [PSCustomObject]@{
            Status     = "Unchanged"
            Skill      = $SkillName
            Category   = $Category
            Source     = $ResolvedSourceSkill
            Destination = $TargetSkillPath
        }

        return
    }

    if (-not $Force) {
        throw @"
A different Hermes skill already exists at:

$TargetSkillPath

Review the differences first. Run again with -Force only when replacement is
intended. A timestamped backup will be created.
"@
    }
}

if ($PSCmdlet.ShouldProcess(
    $TargetSkillPath,
    "Install Hermes compatibility skill"
)) {
    if (-not (Test-Path -LiteralPath $TargetDirectory)) {
        New-Item `
            -ItemType Directory `
            -Path $TargetDirectory `
            -Force |
            Out-Null
    }

    $BackupPath = $null

    if (Test-Path -LiteralPath $TargetSkillPath -PathType Leaf) {
        $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $BackupPath = "$TargetSkillPath.$Timestamp.bak"

        Copy-Item `
            -LiteralPath $TargetSkillPath `
            -Destination $BackupPath
    }

    Copy-Item `
        -LiteralPath $ResolvedSourceSkill `
        -Destination $TargetSkillPath `
        -Force

    $InstalledHash = (
        Get-FileHash -LiteralPath $TargetSkillPath -Algorithm SHA256
    ).Hash

    [PSCustomObject]@{
        Status      = "Installed"
        Skill       = $SkillName
        Category    = $Category
        Source      = $ResolvedSourceSkill
        Destination = $TargetSkillPath
        Backup      = $BackupPath
        SHA256      = $InstalledHash
    }
}