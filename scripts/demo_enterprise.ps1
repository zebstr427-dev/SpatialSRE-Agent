$body = @{
    input = "分析 data-sync-service 发布后的 CPU 告警，关联日志、变更与依赖图"
    incident_id = "demo-enterprise-001"
    execute_remediation = $false
    alert = @{
        alert_name = "HighCPUUsage"
        service = "data-sync-service"
        severity = "critical"
        environment = "production"
        requires_graph_analysis = $true
    }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://localhost:9900/api/enterprise/incidents" -ContentType "application/json" -Body $body | ConvertTo-Json -Depth 12
