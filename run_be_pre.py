import subprocess
import webbrowser

from shell_command_log import log_next_shell_command

# Prompt the user for input
inp = input("Do you need to log in (y/(anything - {y})): ")

if inp == "y":
    # Run AWS SSO login
    # aws sso login --profile devCluster --region eu-central-1
    cmd_aws_sso = ["aws", "sso", "login", "--profile", "devCluster", "--region", "eu-central-1"]
    log_next_shell_command(cmd_aws_sso)
    subprocess.run(cmd_aws_sso)

    # Open Edge with the AWS portal
    webbrowser.open("https://iqviaportal.awsapps.com/start/#/?tab=accounts")

    # Start the AWS SSM session script
    cmd_ssm = ["python", r"C:\Users\u1183836\Documents\work\startup\start_aws_ssm.py"]
    log_next_shell_command(cmd_ssm)
    subprocess.Popen(cmd_ssm, creationflags=subprocess.CREATE_NEW_CONSOLE)

    # Start the connect-cache script
    cmd_cache = ["python", r"C:\Users\u1183836\Documents\work\startup\connect-cache.py"]
    log_next_shell_command(cmd_cache)
    subprocess.Popen(cmd_cache, creationflags=subprocess.CREATE_NEW_CONSOLE)

    # Run AWS CodeArtifact login
    # aws codeartifact login --tool dotnet --repository oa-packages --domain tech-analytics-euf --domain-owner 662744937784 --region eu-central-1 --profile devCluster
    cmd_ca = [
        "aws", "codeartifact", "login",
        "--tool", "dotnet",
        "--repository", "oa-packages",
        "--domain", "tech-analytics-euf",
        "--domain-owner", "662744937784",
        "--region", "eu-central-1",
        "--profile", "devCluster"
    ]
    log_next_shell_command(cmd_ca)
    subprocess.run(cmd_ca)
else:
    # Start the AWS SSM session script
    cmd_ssm = ["python", r"C:\Users\u1183836\Documents\work\startup\start_aws_ssm.py"]
    log_next_shell_command(cmd_ssm)
    subprocess.Popen(cmd_ssm, creationflags=subprocess.CREATE_NEW_CONSOLE)

    # Start the connect-cache script
    cmd_cache = ["python", r"C:\Users\u1183836\Documents\work\startup\connect-cache.py"]
    log_next_shell_command(cmd_cache)
    subprocess.Popen(cmd_cache, creationflags=subprocess.CREATE_NEW_CONSOLE)

