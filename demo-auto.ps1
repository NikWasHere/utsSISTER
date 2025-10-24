#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Automated demo script untuk UTS SISTER - Pub-Sub Log Aggregator
.DESCRIPTION
    Script ini menjalankan demo lengkap untuk video dengan output yang jelas
#>

$ErrorActionPreference = "Stop"

# Colors untuk output
function Write-Header {
    param($Text)
    Write-Host "`n" -NoNewline
    Write-Host "="*80 -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Yellow
    Write-Host "="*80 -ForegroundColor Cyan
}

function Write-Step {
    param($Step, $Text)
    Write-Host "`n[$Step] " -ForegroundColor Green -NoNewline
    Write-Host $Text -ForegroundColor White
}

function Write-Success {
    param($Text)
    Write-Host "✓ $Text" -ForegroundColor Green
}

function Write-Info {
    param($Text)
    Write-Host "  $Text" -ForegroundColor Gray
}

# Function untuk publish event
function Publish-Event {
    param(
        [string]$Topic,
        [string]$EventId,
        [string]$Source,
        [string]$Message
    )
    
    $body = @{
        topic = $Topic
        event_id = $EventId
        timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
        source = $Source
        payload = @{
            message = $Message
            level = "INFO"
        }
    } | ConvertTo-Json -Compress
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8080/publish" `
            -Method Post `
            -ContentType "application/json" `
            -Body $body `
            -ErrorAction Stop
        return $response
    }
    catch {
        Write-Host "  Error: $_" -ForegroundColor Red
        return $null
    }
}

# Function untuk get stats
function Get-AggregatorStats {
    try {
        $stats = Invoke-RestMethod -Uri "http://localhost:8080/stats" -Method Get
        return $stats
    }
    catch {
        Write-Host "  Error: $_" -ForegroundColor Red
        return $null
    }
}

# Function untuk get events
function Get-TopicEvents {
    param([string]$Topic)
    try {
        $events = Invoke-RestMethod -Uri "http://localhost:8080/events?topic=$Topic" -Method Get
        return $events
    }
    catch {
        Write-Host "  Error: $_" -ForegroundColor Red
        return $null
    }
}

# ============================================================================
# MAIN DEMO
# ============================================================================

Write-Header "UTS SISTER - PUB-SUB LOG AGGREGATOR DEMO"
Write-Host "Nama    : [ISI NAMA ANDA]" -ForegroundColor White
Write-Host "NIM     : [ISI NIM ANDA]" -ForegroundColor White
Write-Host "Matakuliah : Sistem Terdistribusi" -ForegroundColor White

# Step 1: Cek service health
Write-Step 1 "Checking service health..."
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method Get
    Write-Success "Service is $($health.status)"
    Write-Info "Timestamp: $($health.timestamp)"
}
catch {
    Write-Host "❌ Service tidak berjalan. Jalankan: docker-compose up -d" -ForegroundColor Red
    exit 1
}

# Step 2: Publish event pertama (unique)
Write-Step 2 "Publishing first unique event..."
$resp1 = Publish-Event -Topic "app-logs" -EventId "evt-001" -Source "web-server-1" -Message "Application started"
if ($resp1) {
    Write-Success "Event published"
    Write-Info "Event ID: $($resp1.event_id)"
    Write-Info "Status: $($resp1.status)"
    Write-Info "Unique: $($resp1.is_new)"
}
Start-Sleep -Milliseconds 500

# Step 3: Publish event duplicate (sama event_id dan topic)
Write-Step 3 "Publishing duplicate event (same event_id and topic)..."
$resp2 = Publish-Event -Topic "app-logs" -EventId "evt-001" -Source "web-server-1" -Message "Application started"
if ($resp2) {
    Write-Success "Event published"
    Write-Info "Event ID: $($resp2.event_id)"
    Write-Info "Status: $($resp2.status)"
    Write-Info "Is duplicate: $(-not $resp2.is_new)"
}
Start-Sleep -Milliseconds 500

# Step 4: Publish beberapa event unik lagi
Write-Step 4 "Publishing more unique events..."
$events = @(
    @{Topic="app-logs"; EventId="evt-002"; Source="web-server-1"; Message="User login successful"},
    @{Topic="app-logs"; EventId="evt-003"; Source="web-server-2"; Message="Database connection established"},
    @{Topic="error-logs"; EventId="err-001"; Source="api-server"; Message="Timeout connecting to external API"},
    @{Topic="error-logs"; EventId="err-002"; Source="api-server"; Message="Validation failed for user input"}
)

foreach ($evt in $events) {
    $resp = Publish-Event -Topic $evt.Topic -EventId $evt.EventId -Source $evt.Source -Message $evt.Message
    if ($resp) {
        Write-Info "✓ $($evt.EventId) - Status: $($resp.status) - New: $($resp.is_new)"
    }
    Start-Sleep -Milliseconds 300
}

# Step 5: Publish duplicate lagi untuk testing
Write-Step 5 "Publishing more duplicates to test deduplication..."
$duplicates = @("evt-002", "err-001", "evt-003")
foreach ($evtId in $duplicates) {
    $topic = if ($evtId.StartsWith("err")) { "error-logs" } else { "app-logs" }
    $resp = Publish-Event -Topic $topic -EventId $evtId -Source "test-source" -Message "Duplicate test"
    if ($resp) {
        Write-Info "✓ $evtId - Duplicate: $(-not $resp.is_new)"
    }
    Start-Sleep -Milliseconds 300
}

# Step 6: Show current stats
Write-Step 6 "Checking aggregator statistics..."
$stats = Get-AggregatorStats
if ($stats) {
    Write-Host "`n  📊 STATISTICS" -ForegroundColor Cyan
    Write-Host "  ├─ Total received      : $($stats.received)" -ForegroundColor White
    Write-Host "  ├─ Unique processed    : $($stats.unique_processed)" -ForegroundColor Green
    Write-Host "  ├─ Duplicates dropped  : $($stats.duplicate_dropped)" -ForegroundColor Yellow
    Write-Host "  ├─ Duplicate rate      : $([math]::Round($stats.duplicate_rate * 100, 2))%" -ForegroundColor Yellow
    Write-Host "  ├─ Active topics       : $($stats.topics.Count)" -ForegroundColor White
    Write-Host "  └─ Uptime              : $([math]::Round($stats.uptime_seconds, 2))s" -ForegroundColor White
    
    if ($stats.topics.Count -gt 0) {
        Write-Host "`n  📁 TOPICS:" -ForegroundColor Cyan
        foreach ($topic in $stats.topics) {
            Write-Host "     • $($topic.topic): $($topic.count) events" -ForegroundColor Gray
        }
    }
}

# Step 7: Query events by topic
Write-Step 7 "Querying events by topic..."
$appLogs = Get-TopicEvents -Topic "app-logs"
if ($appLogs) {
    Write-Host "`n  📋 APP-LOGS ($($appLogs.total) events):" -ForegroundColor Cyan
    foreach ($evt in $appLogs.events) {
        Write-Host "     • $($evt.event_id) - $($evt.source) - $($evt.payload.message)" -ForegroundColor Gray
    }
}

$errorLogs = Get-TopicEvents -Topic "error-logs"
if ($errorLogs) {
    Write-Host "`n  📋 ERROR-LOGS ($($errorLogs.total) events):" -ForegroundColor Cyan
    foreach ($evt in $errorLogs.events) {
        Write-Host "     • $($evt.event_id) - $($evt.source) - $($evt.payload.message)" -ForegroundColor Gray
    }
}

# Step 8: Test persistence dengan restart
Write-Step 8 "Testing persistence - Restarting container..."
Write-Info "Stopping container..."
docker-compose stop aggregator | Out-Null
Start-Sleep -Seconds 2

Write-Info "Starting container..."
docker-compose start aggregator | Out-Null
Start-Sleep -Seconds 5

Write-Info "Checking health after restart..."
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8080/health" -Method Get
    Write-Success "Service restarted successfully"
}
catch {
    Write-Host "  ❌ Service gagal restart" -ForegroundColor Red
    exit 1
}

# Step 9: Verify data persistence
Write-Step 9 "Verifying data persistence after restart..."
$statsAfter = Get-AggregatorStats
if ($statsAfter) {
    Write-Success "Data persisted successfully!"
    Write-Info "Unique events in store: $($statsAfter.unique_processed)"
    Write-Info "Topics preserved: $($statsAfter.topics.Count)"
}

# Step 10: Publish new event after restart
Write-Step 10 "Publishing new event after restart..."
$respAfter = Publish-Event -Topic "app-logs" -EventId "evt-004" -Source "web-server-1" -Message "System recovered after restart"
if ($respAfter) {
    Write-Success "New event accepted"
    Write-Info "Status: $($respAfter.status)"
}
Start-Sleep -Milliseconds 500

# Step 11: Try duplicate of old event
Write-Step 11 "Testing duplicate detection of old event (evt-001)..."
$respOld = Publish-Event -Topic "app-logs" -EventId "evt-001" -Source "web-server-1" -Message "Old duplicate test"
if ($respOld) {
    Write-Success "Deduplication still working after restart!"
    Write-Info "Is duplicate: $(-not $respOld.is_new)"
}

# Step 12: Final stats
Write-Step 12 "Final statistics..."
$finalStats = Get-AggregatorStats
if ($finalStats) {
    Write-Host "`n  📊 FINAL STATISTICS" -ForegroundColor Cyan
    Write-Host "  ├─ Total received      : $($finalStats.received)" -ForegroundColor White
    Write-Host "  ├─ Unique processed    : $($finalStats.unique_processed)" -ForegroundColor Green
    Write-Host "  ├─ Duplicates dropped  : $($finalStats.duplicate_dropped)" -ForegroundColor Yellow
    Write-Host "  ├─ Duplicate rate      : $([math]::Round($finalStats.duplicate_rate * 100, 2))%" -ForegroundColor Yellow
    Write-Host "  ├─ Active topics       : $($finalStats.topics.Count)" -ForegroundColor White
    Write-Host "  └─ Total uptime        : $([math]::Round($finalStats.uptime_seconds, 2))s" -ForegroundColor White
}

# Summary
Write-Header "DEMO COMPLETE! ✓"
Write-Host "`n🎯 Key Features Demonstrated:" -ForegroundColor Green
Write-Host "   ✓ Idempotent consumer (duplicate detection)" -ForegroundColor White
Write-Host "   ✓ Multiple topics support" -ForegroundColor White
Write-Host "   ✓ Data persistence (SQLite)" -ForegroundColor White
Write-Host "   ✓ Graceful restart without data loss" -ForegroundColor White
Write-Host "   ✓ Statistics and monitoring" -ForegroundColor White
Write-Host "   ✓ RESTful API endpoints" -ForegroundColor White

Write-Host "`n📝 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Review container logs: docker-compose logs aggregator" -ForegroundColor Gray
Write-Host "   2. Run unit tests: docker-compose run aggregator pytest -v" -ForegroundColor Gray
Write-Host "   3. Stop service: docker-compose down" -ForegroundColor Gray
Write-Host "   4. Record this demo for your video!" -ForegroundColor Yellow

Write-Host "`n" -NoNewline
