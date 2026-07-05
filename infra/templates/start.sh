#!/bin/bash
cd /opt/atlas/server/fabric
exec java -Xms1G -Xmx4G -jar fabric-server-launch.jar nogui
