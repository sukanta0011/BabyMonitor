# BabyMonitor

## firewall update commands
```bash
# Target the RTSP control port for Camera 1 only
sudo ufw allow proto tcp from 192.168.1.106 to any port 554

# Target the UDP streaming ports for Camera 1 only
sudo ufw allow proto udp from 192.168.1.106 to any port 1024:65535