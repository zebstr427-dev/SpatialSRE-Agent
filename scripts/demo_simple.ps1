$body = @{
    session_id = "demo-simple"
    incident_id = "demo-simple-001"
    input = "检查 data-sync-service 的单一 CPU 告警并给出证据报告"
    strategy = "simple"
    execute_remediation = $false
    alert = @{ alert_name = "HighCPUUsage"; service = "data-sync-service"; severity = "medium" }
} | ConvertTo-Json -Depth 6

$body | curl.exe -N -X POST "http://localhost:9900/api/aiops" -H "Content-Type: application/json" --data-binary "@-"
