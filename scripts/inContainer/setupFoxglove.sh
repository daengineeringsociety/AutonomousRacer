#!/bin/bash

sudo mkdir -p /var/tmp


cat <<EOF | sudo tee /var/tmp/husarnet-cyclone.xml
<?xml version="1.0" encoding="UTF-8" ?>
<CycloneDDS xmlns="https://github.com" xmlns:xsi="http://www.w3.org" xsi:schemaLocation="https://github.com https://raw.githubusercontent.com">
    <Domain id="any">
        <General>
            <NetworkInterfaceAddress>auto</NetworkInterfaceAddress>
        </General>
    </Domain>
</CycloneDDS>
EOF

sudo chmod 644 /var/tmp/husarnet-cyclone.xml