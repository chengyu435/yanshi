#UAV mobile mod
#PC connect to UAV wifi
#set config_tello_sta('RedmiK70', 'Aa123456') as your wifi
#run this script
#change UAV to wifi mod
import socket
import time


def config_tello_sta(ssid, password):
    tello_address = ('192.168.10.1', 8889)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', 9000))
    sock.settimeout(5.0)

    def send_command(cmd):
        print(f"[*] 发送指令: {cmd}")
        sock.sendto(cmd.encode('utf-8'), tello_address)

        try:
            response, addr = sock.recvfrom(1024)
            text = response.decode('utf-8', errors='ignore').strip()
            print(f"[+] 来自 {addr} 的回复: {text}")
            return text
        except socket.timeout:
            print("[-] 请求超时，请确认电脑当前连接的是 Tello 默认 Wi-Fi")
            return None

    try:
        # 1. 进入 SDK 模式
        resp = send_command('command')
        if resp != 'ok':
            print("[!] command 未返回 ok，停止配置")
            return

        time.sleep(1)

        # 2. 配置组网模式
        resp = send_command(f'ap {ssid} {password}')
        if resp and resp.lower().startswith('ok'):
            print("\n[✓] 配网指令已发送成功。")
            print("[!] 无人机会断开 TELLO 默认 Wi-Fi，并尝试连接目标路由器/热点。")
            print("[!] 请等待 20~40 秒，然后让电脑连接同一个路由器/热点，再运行扫描脚本。")
        else:
            print("[!] ap 指令未返回 ok，请检查 SSID/密码。")

    finally:
        sock.close()


if __name__ == '__main__':
    # 建议先用普通路由器，不建议一开始用手机热点
    config_tello_sta('RedmiK70', 'Aa123456')
    # config_tello_sta('zw214', 'zw123456')