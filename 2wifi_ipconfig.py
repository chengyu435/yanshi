# run this mod to get UAV ip + SN
import socket
import subprocess
import re
import time


def get_wifi_ipv4_list():
    """
    从 ipconfig 中提取本机 IPv4 地址。
    会排除常见虚拟网卡、回环地址。
    """
    result = subprocess.check_output(
        "ipconfig",
        shell=True,
        encoding="gbk",
        errors="ignore"
    )

    ips = re.findall(r"IPv4.*?:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", result)

    filtered = []
    for ip in ips:
        if ip.startswith("127."):
            continue
        if ip.startswith("169.254."):
            continue
        if ip.startswith("172."):
            # 有些虚拟网卡是 172.x，可按需保留或排除
            pass
        filtered.append(ip)

    return filtered


def guess_broadcast(ip):
    """
    默认按 /24 网段推算广播地址。
    例如 10.174.64.55 -> 10.174.64.255
    """
    parts = ip.split(".")
    return ".".join(parts[:3]) + ".255"


def send_command_to_tello(target_ip, command, local_ip=None, timeout=2):
    """
    向指定 Tello IP 发送命令，例如 command、sn?、battery?
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)

    try:
        if local_ip:
            sock.bind((local_ip, 0))

        sock.sendto(command.encode("utf-8"), (target_ip, 8889))
        data, addr = sock.recvfrom(1024)
        text = data.decode("utf-8", errors="ignore").strip()
        return text

    except socket.timeout:
        return "timeout"

    except Exception as e:
        return f"error: {e}"

    finally:
        sock.close()


def scan_tello_ips(local_ip, timeout=6):
    """
    第一步：只扫描 IP，不查询 SN。
    这样不会因为查询第一台设备而错过其他设备。
    """
    broadcast_ip = guess_broadcast(local_ip)

    print(f"\n正在通过本机 IP {local_ip} 扫描广播地址 {broadcast_ip} ...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.5)

    found_ips = {}

    try:
        sock.bind((local_ip, 0))

        # 多发几次广播，提高三台都响应的概率
        for _ in range(3):
            sock.sendto(b"command", (broadcast_ip, 8889))
            time.sleep(0.2)

        start = time.time()

        while time.time() - start < timeout:
            try:
                data, addr = sock.recvfrom(1024)
                tello_ip = addr[0]
                text = data.decode("utf-8", errors="ignore").strip()

                if tello_ip == local_ip:
                    continue

                if tello_ip not in found_ips:
                    found_ips[tello_ip] = text
                    print(f"✅ 发现设备: IP={tello_ip}, 响应={text}")

            except socket.timeout:
                continue

        if not found_ips:
            print(f"❌ 在 {broadcast_ip} 未发现 Tello")

        return found_ips

    finally:
        sock.close()


def query_tello_info(local_ip, found_ips):
    """
    第二步：扫描结束后，再逐台查询 SN 和电量。
    """
    devices = []

    for tello_ip, response in found_ips.items():
        print(f"\n正在查询设备信息: {tello_ip}")

        # 保险起见，先对该 IP 单独发送 command
        cmd_resp = send_command_to_tello(
            tello_ip,
            "command",
            local_ip=local_ip,
            timeout=2
        )

        sn = send_command_to_tello(
            tello_ip,
            "sn?",
            local_ip=local_ip,
            timeout=2
        )

        battery = send_command_to_tello(
            tello_ip,
            "battery?",
            local_ip=local_ip,
            timeout=2
        )

        device = {
            "ip": tello_ip,
            "response": response,
            "command_response": cmd_resp,
            "sn": sn,
            "battery": battery,
        }

        devices.append(device)

        print("   IP:", tello_ip)
        print("   command:", cmd_resp)
        print("   SN:", sn)
        print("   电量:", battery)

    return devices


if __name__ == "__main__":
    ip_list = get_wifi_ipv4_list()

    print("检测到本机 IPv4：")
    for ip in ip_list:
        print(" -", ip)

    all_devices = []

    for local_ip in ip_list:
        found_ips = scan_tello_ips(local_ip, timeout=6)

        if found_ips:
            devices = query_tello_info(local_ip, found_ips)
            all_devices.extend(devices)

    if not all_devices:
        print("\n未扫描到 Tello。")
        print("请确认：")
        print("1. 无人机已经成功连接到同一个路由器/热点；")
        print("2. 电脑也连接到同一个路由器/热点；")
        print("3. 路由器/手机热点未开启客户端隔离；")
        print("4. 可以在路由器后台查看是否出现 Tello 设备。")

    else:
        print("\n========== 扫描汇总 ==========")

        for idx, dev in enumerate(all_devices, start=1):
            print(
                f"{idx}. IP: {dev['ip']} | "
                f"SN: {dev['sn']} | "
                f"Battery: {dev['battery']}%"
            )

        print("\n可直接复制到多机控制代码：")
        print("DRONE_IPS = [")
        for dev in all_devices:
            print(f'    "{dev["ip"]}",  # SN: {dev["sn"]}, Battery: {dev["battery"]}%')
        print("]")