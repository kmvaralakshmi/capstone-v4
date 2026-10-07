param(
    [int]$Limit = 0,
    [switch]$Overwrite,
    [string]$OutputDir = (Join-Path $PSScriptRoot '..\brsr-pdfs'),
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

$baseDir = Resolve-Path (Join-Path $PSScriptRoot '..')
$datasetPath = Join-Path $baseDir 'Capstone-project-phase2\capstone-datasets\indian_companies_esg_scores.csv'
$pageUrl = 'https://www.nseindia.com/companies-listing/corporate-filings-bussiness-sustainabilitiy-reports'
$apiUrl = 'https://www.nseindia.com/api/corporate-bussiness-sustainabilitiy?index=equities&csv=true'

function Normalize-Text {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return '' }
    $normalized = ($Value.ToLowerInvariant() -replace '[^a-z0-9]+', ' ').Trim()
    return ($normalized -replace '\s+', ' ')
}

function Get-CompanyCode {
    param([string]$Ticker)
    return (($Ticker -split '\.')[0] -replace '[^A-Za-z0-9]', '').ToUpperInvariant()
}

function Get-Score {
    param(
        [string]$Target,
        [string]$Listing
    )

    $targetNorm = Normalize-Text $Target
    $listingNorm = Normalize-Text $Listing
    if (-not $targetNorm -or -not $listingNorm) { return 0 }
    if ($targetNorm -eq $listingNorm) { return 100 }
    if ($targetNorm.Contains($listingNorm) -or $listingNorm.Contains($targetNorm)) { return 90 }

    $targetTokens = [System.Collections.Generic.HashSet[string]]::new([string[]]($targetNorm -split ' '))
    $listingTokens = [System.Collections.Generic.HashSet[string]]::new([string[]]($listingNorm -split ' '))
    $overlap = 0
    foreach ($token in $targetTokens) {
        if ($listingTokens.Contains($token)) { $overlap++ }
    }
    if ($overlap -eq 0) { return 0 }
    return [int](($overlap / [math]::Max($targetTokens.Count, $listingTokens.Count)) * 80)
}

function Get-BestMatch {
    param(
        [string]$CompanyName,
        [object[]]$Rows
    )

    $bestRow = $null
    $bestScore = 0
    foreach ($row in $Rows) {
        $score = Get-Score -Target $CompanyName -Listing $row.'COMPANY '
        if ($score -gt $bestScore) {
            $bestScore = $score
            $bestRow = $row
        }
    }
    if ($bestScore -ge 60) { return $bestRow }
    return $null
}

function Get-Filename {
    param(
        [string]$CompanyCode,
        [object]$Row,
        [string]$SourceUrl
    )

    $fromYearValue = $Row.'FROM YEAR '
    $toYearValue = $Row.'TO YEAR '
    $fromYear = if ($null -ne $fromYearValue) { $fromYearValue.ToString().Trim() } else { '' }
    $toYear = if ($null -ne $toYearValue) { $toYearValue.ToString().Trim() } else { '' }
    $suffix = 'BRSR'
    if ($fromYear -match '^\d+$' -and $toYear -match '^\d+$') {
        $suffix = '{0}-{1}' -f $fromYear.Substring([math]::Max(0, $fromYear.Length - 2)), $toYear.Substring([math]::Max(0, $toYear.Length - 2))
    } elseif ($SourceUrl.ToLowerInvariant().EndsWith('.pdf')) {
        $suffix = 'latest'
    }
    return '{0}_BR_{1}.pdf' -f $CompanyCode, $suffix
}

$cookieContainer = New-Object System.Net.CookieContainer
$handler = New-Object System.Net.Http.HttpClientHandler
$handler.CookieContainer = $cookieContainer
$handler.UseCookies = $true
$client = New-Object System.Net.Http.HttpClient($handler)
$client.Timeout = [TimeSpan]::FromSeconds(120)
$client.DefaultRequestHeaders.Add('accept', 'text/csv,application/json;q=0.9,*/*;q=0.8')
$client.DefaultRequestHeaders.Add('accept-language', 'en-US,en;q=0.9')
$client.DefaultRequestHeaders.Add('cache-control', 'no-cache')
$client.DefaultRequestHeaders.Add('pragma', 'no-cache')
$client.DefaultRequestHeaders.Add('referer', $pageUrl)
$client.DefaultRequestHeaders.Add('user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36')
$client.DefaultRequestHeaders.Add('x-requested-with', 'XMLHttpRequest')

function Get-HttpText {
    param([string]$Url)

    $response = $client.GetAsync($Url).GetAwaiter().GetResult()
    $response.EnsureSuccessStatusCode() | Out-Null
    return $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
}

function Save-HttpFile {
    param(
        [string]$Url,
        [string]$Destination
    )

    $response = $client.GetAsync($Url).GetAwaiter().GetResult()
    $response.EnsureSuccessStatusCode() | Out-Null
    $bytes = $response.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
    [System.IO.File]::WriteAllBytes($Destination, $bytes)
}

$null = Get-HttpText -Url $pageUrl
$csvText = Get-HttpText -Url $apiUrl
$listingRows = $csvText | ConvertFrom-Csv
$companies = Import-Csv -Path $datasetPath
if ($Limit -gt 0) {
    $companies = $companies | Select-Object -First $Limit
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$downloaded = 0
$skipped = 0
$missing = 0

foreach ($company in $companies) {
    $companyName = $company.Company
    $ticker = $company.Ticker
    $companyCode = Get-CompanyCode -Ticker $ticker
    $match = Get-BestMatch -CompanyName $companyName -Rows $listingRows

    if (-not $match) {
        $missing++
        Write-Host ('MISS  {0}: {1}' -f $companyCode, $companyName)
        continue
    }

    $attachmentUrl = $match.'ATTACHMENT '
    if ([string]::IsNullOrWhiteSpace($attachmentUrl)) {
        $missing++
        Write-Host ('MISS  {0}: no attachment URL found' -f $companyCode)
        continue
    }

    $fileName = Get-Filename -CompanyCode $companyCode -Row $match -SourceUrl $attachmentUrl
    $destination = Join-Path $OutputDir $fileName

    if ($DryRun) {
        Write-Host ('MATCH {0}: {1} -> {2}' -f $companyCode, $companyName, $fileName)
        continue
    }

    if ((Test-Path $destination) -and -not $Overwrite) {
        $skipped++
        Write-Host ('SKIP  {0}: {1}' -f $companyCode, $destination)
        continue
    }

    Save-HttpFile -Url $attachmentUrl -Destination $destination
    $downloaded++
    Write-Host ('OK    {0}: {1}' -f $companyCode, $destination)
}

Write-Host ('Done. targets={0} downloaded={1} skipped={2} missing={3} output_dir={4}' -f $companies.Count, $downloaded, $skipped, $missing, $OutputDir)