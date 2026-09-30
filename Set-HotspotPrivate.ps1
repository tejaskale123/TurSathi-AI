# TurSathi AI - Auto Set WiFi Hotspot to Private Network
# This script sets any Wi-Fi adapter to "Private" so the Windows Firewall
# does not block inbound connections on development ports (8000, 8081).
# 
# Schedule this to run at login or on network change.

$adapters = @("Wi-Fi", "Wi-Fi 2", "Wi-Fi 3", "WLAN")

foreach ($adapter in $adapters) {
    try {
        $profile = Get-NetConnectionProfile -InterfaceAlias $adapter -ErrorAction SilentlyContinue
        if ($profile -and $profile.NetworkCategory -eq "Public") {
            Set-NetConnectionProfile -InterfaceAlias $adapter -NetworkCategory Private
            Write-Host "[TurSathi] '$adapter' changed from Public -> Private (Firewall dev ports now open)" -ForegroundColor Green
        } elseif ($profile) {
            Write-Host "[TurSathi] '$adapter' is already '$($profile.NetworkCategory)' - no change needed." -ForegroundColor Cyan
        }
    } catch {
        Write-Host "[TurSathi] Could not change '$adapter': $_" -ForegroundColor Yellow
    }
}

Write-Host "`n[TurSathi] Done. Backend port 8000 and Expo port 8081 are now accessible from your mobile device." -ForegroundColor Green
