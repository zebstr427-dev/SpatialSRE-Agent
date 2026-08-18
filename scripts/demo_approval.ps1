$incidentId = "demo-approval-001"
$body = @{
    input = "分析 data-sync-service CPU 告警，并为确认的根因生成受控处置"
    incident_id = $incidentId
    execute_remediation = $true
    identity = @{
        identity_id = "demo-operator"
        role = "operator"
        tool_scope = @("*")
        service_scope = @("data-sync-service")
        risk_ceiling = "write"
    }
    alert = @{
        alert_name = "HighCPUUsage"
        service = "data-sync-service"
        severity = "critical"
        environment = "production"
    }
} | ConvertTo-Json -Depth 8

Invoke-RestMethod -Method Post -Uri "http://localhost:9900/api/enterprise/incidents" -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 12

Write-Host "If the state contains a pending approval, resume it with:"
$decision = @{ approved = $true; decided_by = "demo-operator"; reason = "demo dry-run only" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:9900/api/incidents/$incidentId/approval" -ContentType "application/json" -Body $decision | ConvertTo-Json -Depth 12
