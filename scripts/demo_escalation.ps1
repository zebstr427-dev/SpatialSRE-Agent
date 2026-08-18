$body = @{
    session_id = "demo-escalation"
    incident_id = "demo-escalation-001"
    input = "排查 data-sync-service 的间歇性延迟；只接受可引用的工具证据"
    strategy = "auto"
    execute_remediation = $false
    alert = @{ alert_name = "IntermittentLatency"; service = "data-sync-service"; severity = "medium" }
} | ConvertTo-Json -Depth 6

$body | curl.exe -N -X POST "http://localhost:9900/api/aiops" -H "Content-Type: application/json" --data-binary "@-"
