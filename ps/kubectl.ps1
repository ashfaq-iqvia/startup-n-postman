$inp = Read-Host "dev? (y(yes)/(anything - {y}))"
$copyFromAppSettings = Read-Host "copy? (y(yes)/(anything - {y}))"
if ($inp -eq "y") {
    if($copyFromAppSettings -eq "y")
    {
        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\dev\config\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Configuration\src\PMI.Service.Configuration\appsettings.Development.json"

        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\dev\migration\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Migration\src\PMI.Service.Migration\appsettings.Development.json"

        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\dev\dashboard\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Dashboard\src\PMI.Service.Dashboard\appsettings.Development.json"

        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\dev\export\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Export\src\PMI.Service.Export\appsettings.Development.json"

        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\dev\mapShapeGen\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_MapShapeGen\src\PMI.Service.Map\appsettings.Development.json"

        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\dev\widget template editor\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_WidgetTemplateEditor\src\PMI.Service.WidgetTemplateEditor\appsettings.Development.json"
    }


    while ($true) {
        Write-Host "Starting port-forward (dev)..." -ForegroundColor Green

        # kubectl --context pl-euf-kpi --namespace oa-pl-euf-kpideveloper-kpi01-dev01-kpidev port-forward pods/core-cache-service-0 30017:27017
        # kubectl --context pl-euf-kpi --namespace oa-pl-euf-kpideveloper-kpi01-dev01-kpidev port-forward pods/core-cache-service-1 30017:27017
        kubectl --context pl-euf-kpi -n commons port-forward pods/core-cache-service-0 27018:27017
        # kubectl --context pl-euf-kpi --namespace oa-pl-euf-kpideveloper-kpi01-dev01-kpidev port-forward services/core-cache-service-svc 27018:27017 -n commons

        Write-Host "Disconnected. Reconnecting in 3s..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }
}
else {
    if($copyFromAppSettings -eq "y")
    {
        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\predev\config\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Configuration\src\PMI.Service.Configuration\appsettings.Development.json"

        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\predev\migration\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Migration\src\PMI.Service.Migration\appsettings.Development.json"

        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\predev\dashboard\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Dashboard\src\PMI.Service.Dashboard\appsettings.Development.json"

        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\predev\export\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_Export\src\PMI.Service.Export\appsettings.Development.json"

        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\predev\mapShapeGen\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_MapShapeGen\src\PMI.Service.Map\appsettings.Development.json"

        Get-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\appsettings\new format\predev\widget template editor\appsettings.Development.json" | Set-Content -Path "C:\Users\u1183836\Documents\work\project\KPI\service\PMI_Service_WidgetTemplateEditor\src\PMI.Service.WidgetTemplateEditor\appsettings.Development.json"
    }

    while ($true) {
        Write-Host "Starting port-forward (predev)..." -ForegroundColor Green

        # kubectl --context pl-euf-kpi --namespace oa-pl-euf-kpideveloper-kpi01-dev01-kpipredev port-forward pods/core-cache-service-0 30017:27017
        # kubectl --context pl-euf-kpi --namespace oa-pl-euf-kpideveloper-kpi01-dev01-kpipredev port-forward pods/core-cache-service-1 30017:27017
        kubectl --context pl-euf-kpi --namespace oa-pl-euf-kpideveloper-kpi01-dev01-kpipredev port-forward pods/core-cache-service-0 27018:27017 -n commons
        # kubectl --context pl-euf-kpi --namespace oa-pl-euf-kpideveloper-kpi01-dev01-kpipredev port-forward services/core-cache-service-svc 27018:27017 -n commons

        Write-Host "Disconnected. Reconnecting in 3s..." -ForegroundColor Yellow
        Start-Sleep -Seconds 3
    }
}

aws eks update-kubeconfig --name oa-pl-euf-kpideveloper-kpi01 --region eu-central-1 --role-arn arn:aws:iam::662744937784:role/PL_OA-oa-pl-euf-kpideveloper-kpi01-eks-admin  --profile devCluster --alias pl-euf-kpi
