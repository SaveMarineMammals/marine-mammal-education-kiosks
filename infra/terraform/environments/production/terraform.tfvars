aws_region    = "us-east-1"
environment   = "production"
project_name  = "mmek"
parent_domain = "savemarinemammals.com"

# Facility CMS (kiosk-server). Update if the host IP changes.
cms_server_ipv4 = "10.1.10.140"

create_acme_access_key = true

tags = {
  Facility = "belize"
}
