#single UAV control
import time
import threading
import pygame
import cv2
from djitellopy import Tello

# =========================
# 网络设置
# =========================
# 组网模式下，填写你扫描到的无人机 IP
TELLO_IP = "10.110.204.199"

# 如果是直连 Tello 默认 Wi-Fi，可以改成：
# TELLO_IP = "192.168.10.1"

# =========================
# 显示与控制参数
# =========================
WINDOW_WIDTH = 1080
WINDOW_HEIGHT = 720

SPEED = 30

CONTROL_FPS = 50
VIDEO_FPS = 15

RC_SEND_INTERVAL = 1.0 / CONTROL_FPS
VIDEO_INTERVAL = 1.0 / VIDEO_FPS

# =========================
# 全局状态
# =========================
running = True
is_flying = False

latest_frame = None
frame_lock = threading.Lock()


# =========================
# 视频读取线程
# =========================
def video_reader_loop(frame_read):
    """
    独立线程持续读取最新视频帧。
    只保存最新一帧，旧帧直接丢弃，避免视频影响控制。
    """
    global latest_frame, running

    while running:
        try:
            frame = frame_read.frame
            if frame is not None:
                with frame_lock:
                    latest_frame = frame
        except Exception as e:
            print("video read error:", e)

        time.sleep(0.002)


def main():
    global running, is_flying, latest_frame

    # =========================
    # 初始化 pygame
    # =========================
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Tello Keyboard Control")
    clock = pygame.time.Clock()

    # =========================
    # 初始化 Tello
    # =========================
    print(f"Connecting to Tello: {TELLO_IP}")

    drone = Tello(host=TELLO_IP)
    drone.connect()

    battery = drone.get_battery()
    print("Battery:", battery)

    # =========================
    # 启动视频流
    # =========================
    try:
        drone.streamoff()
        time.sleep(0.5)
    except Exception as e:
        print("streamoff warning:", e)

    drone.streamon()
    time.sleep(2)

    frame_read = drone.get_frame_read()

    # 启动视频读取线程
    video_thread = threading.Thread(
        target=video_reader_loop,
        args=(frame_read,),
        daemon=True
    )
    video_thread.start()

    last_rc_time = 0
    last_video_time = 0

    print("\n控制说明：")
    print("Tab        起飞")
    print("Backspace  降落")
    print("W/S        前进/后退")
    print("A/D        左移/右移")
    print("Space      上升")
    print("Shift      下降")
    print("Q/E        左转/右转")
    print("Esc        退出程序\n")

    try:
        while running:
            now = time.time()

            # =========================
            # 处理键盘事件：起飞、降落、退出
            # =========================
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False

                    elif event.key == pygame.K_TAB:
                        if not is_flying:
                            print("Takeoff")
                            drone.takeoff()
                            is_flying = True

                    elif event.key == pygame.K_BACKSPACE:
                        if is_flying:
                            print("Land")
                            drone.send_rc_control(0, 0, 0, 0)
                            time.sleep(0.2)
                            drone.land()
                            is_flying = False

            # =========================
            # 高频控制循环
            # =========================
            if now - last_rc_time >= RC_SEND_INTERVAL:
                keys = pygame.key.get_pressed()

                left_right = 0
                forward_backward = 0
                up_down = 0
                yaw = 0

                # A / D：左右平移
                if keys[pygame.K_a]:
                    left_right = -SPEED
                elif keys[pygame.K_d]:
                    left_right = SPEED

                # W / S：前进后退
                if keys[pygame.K_w]:
                    forward_backward = SPEED
                elif keys[pygame.K_s]:
                    forward_backward = -SPEED

                # Space / Shift：上升下降
                if keys[pygame.K_SPACE]:
                    up_down = SPEED
                elif keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                    up_down = -SPEED

                # Q / E：旋转
                if keys[pygame.K_q]:
                    yaw = -SPEED
                elif keys[pygame.K_e]:
                    yaw = SPEED

                if is_flying:
                    try:
                        drone.send_rc_control(
                            left_right,
                            forward_backward,
                            up_down,
                            yaw
                        )
                    except Exception as e:
                        print("rc control error:", e)

                last_rc_time = now

            # =========================
            # 低频视频显示
            # =========================
            if now - last_video_time >= VIDEO_INTERVAL:
                frame = None

                with frame_lock:
                    if latest_frame is not None:
                        frame = latest_frame.copy()

                if frame is not None:
                    try:
                        # djitellopy 获取到的通常是 BGR，pygame 需要 RGB
                        # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                        # 缩放到窗口尺寸
                        frame = cv2.resize(frame, (WINDOW_WIDTH, WINDOW_HEIGHT))

                        # 转成 pygame surface
                        frame_surface = pygame.surfarray.make_surface(
                            frame.swapaxes(0, 1)
                        )

                        screen.blit(frame_surface, (0, 0))
                        pygame.display.update()

                    except Exception as e:
                        print("video display error:", e)

                last_video_time = now

            # 主循环限速，避免 CPU 占用过高
            clock.tick(80)

    except KeyboardInterrupt:
        print("退出程序")

    finally:
        print("Shutting down connection to drone...")
        running = False

        try:
            if is_flying:
                drone.send_rc_control(0, 0, 0, 0)
                time.sleep(0.2)
                drone.land()
                time.sleep(2)
        except Exception as e:
            print("land error:", e)

        try:
            drone.streamoff()
        except Exception as e:
            print("streamoff error:", e)

        try:
            drone.end()
        except Exception as e:
            print("drone end error:", e)

        pygame.quit()


if __name__ == '__main__':
    main()