import subprocess

hash_str = "$2a$12$qlJdAgcMTCxRuetY83cvI.rGfDu2eqeqCMjk3TnthYcbBxRsqvhNm"
cmd = [
    "ssh", "-i", "cloud_computing_key.pem", "-o", "StrictHostKeyChecking=no", "ec2-user@34.227.190.50",
    f"sudo docker rm -f wg-easy; sudo docker run -d --name=wg-easy -e WG_HOST=34.227.190.50 -e PASSWORD_HASH='{hash_str}' -v /etc/wireguard:/etc/wireguard -p 51820:51820/udp -p 51821:51821/tcp --cap-add=NET_ADMIN --cap-add=SYS_MODULE --sysctl=net.ipv4.conf.all.src_valid_mark=1 --sysctl=net.ipv4.ip_forward=1 --restart always ghcr.io/wg-easy/wg-easy"
]
subprocess.run(cmd)
