# aws ssm start-session --region eu-central-1 --profile devCluster --target i-081b4614582b0f0b3 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host=endpoint-662744937784-vpc-0e59349699577a37a-964mx2.endpoint.proxy-cefekb6lills.eu-central-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5433
# aws ssm start-session --region eu-central-1 --target i-08acabe420a38c420 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host="oa-euf-shared-postgresql-db-aurora-dev-one.cefekb6lills.eu-central-1.rds.amazonaws.com",portNumber="5432",localPortNumber="5432" --profile 133460326175
# aws ssm start-session --region eu-central-1 --target  i-05d95e75dace1dc79 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host=endpoint-662744937784-vpc-0e59349699577a37a-964mx2.endpoint.proxy-cefekb6lills.eu-central-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5433 --profile devCluster




while ($true) {
    Write-Host "Starting SSM session..." -ForegroundColor Green

    # Test mode: 5 second timeout
    $process = Start-Process -FilePath "aws" -ArgumentList "ssm start-session --region eu-central-1 --target i-0c2622bfb22da2f9f --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host=endpoint-662744937784-vpc-0e59349699577a37a-964mx2.endpoint.proxy-cefekb6lills.eu-central-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5433 --profile devCluster" -PassThru -NoNewWindow
    Start-Sleep -Seconds 15
    if (!$process.HasExited) { Stop-Process -Id $process.Id -Force }

    # Original (uncomment for normal use):
    # aws ssm start-session --region eu-central-1 --target  i-083e36595ba7a0c28 --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters host=endpoint-662744937784-vpc-0e59349699577a37a-964mx2.endpoint.proxy-cefekb6lills.eu-central-1.rds.amazonaws.com,portNumber=5432,localPortNumber=5433 --profile devCluster

    Write-Host "Disconnected. Press Enter to reconnect now, or wait 15 minutes..." -ForegroundColor Yellow
    $endTime = (Get-Date).AddMinutes(15)
    while ((Get-Date) -lt $endTime) {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            if ($key.Key -eq 'Enter') {
                Write-Host "Reconnecting now!" -ForegroundColor Cyan
                break
            }
        }
        Start-Sleep -Seconds 2
    }
}