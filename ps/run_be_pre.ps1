# Prompt the user for input
$inp = Read-Host "Do you need to log in (y/(anything - {y}))"
if ($inp -eq "y") {
    Workflow Test-Workflow
    {
        Sequence
        {
            aws sso login --profile devCluster --region eu-central-1
            Start-Process msedge.exe '--new-tab https://iqviaportal.awsapps.com/start/#/?tab=accounts'
            Start-Process -FilePath "C:\Users\u1183836\Documents\BE\rds\start_session.ps1"
            Start-Process -FilePath "C:\Users\u1183836\Documents\BE\mongo\kubectl.ps1"  -WindowStyle Normal
            aws codeartifact login --tool dotnet --repository oa-packages --domain tech-analytics-euf --domain-owner 662744937784 --region eu-central-1 --profile devCluster
        }
    }
    Test-Workflow
}
else {
    Start-Process -FilePath "C:\Users\u1183836\Documents\BE\rds\start_session.ps1"  -WindowStyle Normal
    Start-Process -FilePath "C:\Users\u1183836\Documents\BE\mongo\kubectl.ps1"  -WindowStyle Normal
}
