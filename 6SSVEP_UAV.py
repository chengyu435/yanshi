# -*- coding: utf-8 -*-

"""
=========================================================
Tello无人机视频背景 + SSVEP五目标刺激范式

功能：
1. Tello实时视频作为背景
2. 屏幕刷新率：60 Hz
3. 无人机视频刷新率：15 FPS
4. 五个SSVEP目标：

       F = Forward   前进     6 Hz
       B = Backward  后退     7.5 Hz
       L = Left      左移     8.57 Hz
       R = Right     右移     10 Hz
       T = Takeoff   起飞     12 Hz

5. 白色方块整体闪烁
6. 英文字母标注
7. ESC退出

当前版本：
只负责视频 + SSVEP刺激显示
暂时不加入CCA和无人机控制
=========================================================
"""

import time
import threading

import pygame
import cv2

from djitellopy import Tello


# =========================================================
# Tello网络设置
# =========================================================

TELLO_IP = "10.110.204.199"

# 如果使用Tello默认直连WiFi：
# TELLO_IP = "192.168.10.1"


# =========================================================
# 显示参数
# =========================================================

WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

# SSVEP显示刷新率
SCREEN_FPS = 60

# 无人机视频刷新率
VIDEO_FPS = 15

# 60 / 15 = 4
# 所以每4个屏幕刷新周期更新一次视频
VIDEO_FRAME_INTERVAL = SCREEN_FPS // VIDEO_FPS


# =========================================================
# SSVEP参数
# =========================================================

FREQ = [
    6.0,       # F 前进
    7.5,       # B 后退
    8.57,      # L 左移
    10.0,      # R 右移
    12.0       # T 起飞
]

LABELS = [
    "F",
    "B",
    "L",
    "R",
    "T"
]

N = len(FREQ)



POS = [
    # F 前进
    (
        WINDOW_WIDTH // 2,
        WINDOW_HEIGHT // 2 - 300
    ),

    # B 后退
    (
        WINDOW_WIDTH // 2,
        WINDOW_HEIGHT // 2 + 300
    ),

    # L 左移
    (
        WINDOW_WIDTH // 2 - 600,
        WINDOW_HEIGHT // 2
    ),

    # R 右移
    (
        WINDOW_WIDTH // 2 + 600,
        WINDOW_HEIGHT // 2
    ),

    # T 起飞
    (
        WINDOW_WIDTH // 2,
        WINDOW_HEIGHT // 2
    )
]


# =========================================================
# 刺激方框
# =========================================================

BOX_SIZE = 180


# =========================================================
# 字体参数
# =========================================================

FONT_SIZE = 48


# =========================================================
# 视频背景亮度
# =========================================================

# 1.0 = 原始视频
# 0.5 = 亮度减半
# 0.4 = 更暗
# 建议0.45左右
VIDEO_BRIGHTNESS = 0.45


# =========================================================
# 全局变量
# =========================================================

running = True

latest_frame = None

frame_lock = threading.Lock()


# =========================================================
# Tello视频读取线程
# =========================================================

def video_reader_loop(frame_read):

    global latest_frame
    global running

    while running:

        try:

            frame = frame_read.frame

            if frame is not None:

                with frame_lock:

                    latest_frame = frame.copy()

        except Exception as e:

            print(
                "video read error:",
                e
            )

        time.sleep(0.002)


# =========================================================
# OpenCV图像 → Pygame Surface
# =========================================================

def frame_to_surface(frame):

    # -----------------------------------------------------
    # 调整视频尺寸
    # -----------------------------------------------------

    frame = cv2.resize(
        frame,
        (
            WINDOW_WIDTH,
            WINDOW_HEIGHT
        ),
        interpolation=cv2.INTER_LINEAR
    )



    surface = pygame.surfarray.make_surface(
        frame.swapaxes(0, 1)
    )


    return surface




# =========================================================
# 创建刺激方框
# =========================================================

def create_stimulus_rects():

    rects = []

    for x, y in POS:

        rect = pygame.Rect(
            0,
            0,
            BOX_SIZE,
            BOX_SIZE
        )

        rect.center = (
            x,
            y
        )

        rects.append(rect)

    return rects


# =========================================================
# 主程序
# =========================================================

def main():

    global running
    global latest_frame


    # =====================================================
    # 初始化Pygame
    # =====================================================

    pygame.init()


    screen = pygame.display.set_mode(
        (
            WINDOW_WIDTH,
            WINDOW_HEIGHT
        )
    )


    pygame.display.set_caption(
        "Tello SSVEP UAV"
    )


    clock = pygame.time.Clock()


    # =====================================================
    # 使用Pygame默认字体
    # =====================================================

    font = pygame.font.Font(
        None,
        FONT_SIZE
    )


    # =====================================================
    # 颜色
    # =====================================================

    BLACK = (
        0,
        0,
        0
    )

    WHITE = (
        255,
        255,
        255
    )

    RED = (
        255,
        0,
        0
    )


    # =====================================================
    # 创建刺激方框
    # =====================================================

    rects = create_stimulus_rects()


    # =====================================================
    # 创建英文字母
    # =====================================================

    text_surfaces = []

    for label in LABELS:

        surface = font.render(
            label,
            True,
            RED
        )

        text_surfaces.append(
            surface
        )


    # =====================================================
    # 连接Tello
    # =====================================================

    print()
    print(
        "Connecting to Tello:",
        TELLO_IP
    )


    drone = Tello(
        host=TELLO_IP
    )


    try:

        drone.connect()

    except Exception as e:

        print(
            "Tello connection failed:",
            e
        )

        pygame.quit()

        return


    # =====================================================
    # 获取电量
    # =====================================================

    try:

        battery = drone.get_battery()

        print(
            "Battery:",
            battery,
            "%"
        )

    except Exception as e:

        print(
            "Battery read error:",
            e
        )


    # =====================================================
    # 启动视频流
    # =====================================================

    try:

        drone.streamoff()

        time.sleep(
            0.5
        )

    except Exception as e:

        print(
            "streamoff warning:",
            e
        )


    try:

        drone.streamon()

        time.sleep(
            2
        )

    except Exception as e:

        print(
            "streamon error:",
            e
        )

        try:

            drone.end()

        except:

            pass

        pygame.quit()

        return


    # =====================================================
    # 获取视频读取对象
    # =====================================================

    frame_read = drone.get_frame_read()


    # =====================================================
    # 启动视频读取线程
    # =====================================================

    video_thread = threading.Thread(
        target=video_reader_loop,
        args=(
            frame_read,
        ),
        daemon=True
    )

    video_thread.start()


    # =====================================================
    # 等待第一帧
    # =====================================================

    print(
        "Waiting for first video frame..."
    )


    start_time = time.time()


    while latest_frame is None:

        if (
            time.time()
            - start_time
            > 10
        ):

            print(
                "Warning: video frame timeout."
            )

            break

        time.sleep(
            0.05
        )


    # =====================================================
    # 初始视频Surface
    # =====================================================

    video_surface = None


    with frame_lock:

        if latest_frame is not None:

            try:

                video_surface = frame_to_surface(
                    latest_frame
                )

            except Exception as e:

                print(
                    "Initial video processing error:",
                    e
                )


    # =====================================================
    # SSVEP帧计数
    # =====================================================

    frame_count = 0


    # =====================================================
    # 视频帧计数
    # =====================================================

    video_frame_counter = 0


    # =====================================================
    # 输出参数
    # =====================================================

    print()
    print(
        "=========================================="
    )

    print(
        "Tello SSVEP stimulation started"
    )

    print(
        "=========================================="
    )

    print(
        f"Screen refresh : {SCREEN_FPS} Hz"
    )

    print(
        f"Video refresh  : {VIDEO_FPS} FPS"
    )

    print()

    print(
        "SSVEP targets:"
    )

    print(
        "F : Forward   6 Hz"
    )

    print(
        "B : Backward  7.5 Hz"
    )

    print(
        "L : Left      8.57 Hz"
    )

    print(
        "R : Right     10 Hz"
    )

    print(
        "T : Takeoff   12 Hz"
    )

    print()

    print(
        "Press ESC to exit."
    )

    print(
        "=========================================="
    )

    print()


    # =====================================================
    # 主循环
    # =====================================================

    try:

        while running:


            # =================================================
            # 处理键盘事件
            # =================================================

            for event in pygame.event.get():

                if event.type == pygame.QUIT:

                    running = False


                elif event.type == pygame.KEYDOWN:

                    if event.key == pygame.K_ESCAPE:

                        running = False


            # =================================================
            # SSVEP帧计数
            # =================================================

            frame_count += 1


            # =================================================
            # 视频更新
            #
            # 60 Hz / 15 FPS = 4
            #
            # 每4个显示帧更新一次背景
            # =================================================

            video_frame_counter += 1


            if (
                video_frame_counter
                >= VIDEO_FRAME_INTERVAL
            ):

                video_frame_counter = 0


                frame = None


                with frame_lock:

                    if latest_frame is not None:

                        frame = latest_frame.copy()


                if frame is not None:

                    try:

                        video_surface = frame_to_surface(
                            frame
                        )

                    except Exception as e:

                        print(
                            "Video processing error:",
                            e
                        )


            # =================================================
            # 绘制视频背景
            # =================================================

            if video_surface is not None:

                screen.blit(
                    video_surface,
                    (
                        0,
                        0
                    )
                )

            else:

                screen.fill(
                    BLACK
                )


            # =================================================
            # 绘制SSVEP刺激
            # =================================================

            for i in range(N):


                # -------------------------------------------------
                # 计算周期
                # -------------------------------------------------

                period = (
                    SCREEN_FPS
                    / FREQ[i]
                )


                # -------------------------------------------------
                # 当前周期位置
                # -------------------------------------------------

                phase = (
                    frame_count
                    % round(period)
                )


                # -------------------------------------------------
                # 闪烁
                # -------------------------------------------------

                if phase < (
                    period / 2
                ):

                    stim_color = WHITE

                else:

                    stim_color = BLACK


                # -------------------------------------------------
                # 绘制刺激方块
                # -------------------------------------------------

                pygame.draw.rect(
                    screen,
                    stim_color,
                    rects[i]
                )


                # -------------------------------------------------
                # 绘制字母
                #
                # 字母位于方框上方
                # -------------------------------------------------

                text_rect = (
                    text_surfaces[i]
                    .get_rect()
                )


                text_rect.centerx = (
                    POS[i][0]
                )


                text_rect.bottom = (
                    rects[i].top
                    - 25
                )


                screen.blit(
                    text_surfaces[i],
                    text_rect
                )


            # =================================================
            # 屏幕刷新
            # =================================================

            pygame.display.flip()


            # =================================================
            # 60 Hz限速
            # =================================================

            clock.tick(
                SCREEN_FPS
            )


    except KeyboardInterrupt:

        print(
            "Program interrupted."
        )


    finally:

        # =====================================================
        # 程序退出
        # =====================================================

        print()
        print(
            "Shutting down..."
        )


        running = False


        # -----------------------------------------------------
        # 关闭视频流
        # -----------------------------------------------------

        try:

            drone.streamoff()

        except Exception as e:

            print(
                "streamoff error:",
                e
            )


        # -----------------------------------------------------
        # 关闭Tello
        # -----------------------------------------------------

        try:

            drone.end()

        except Exception as e:

            print(
                "drone end error:",
                e
            )


        # -----------------------------------------------------
        # 关闭Pygame
        # -----------------------------------------------------

        pygame.quit()


        print(
            "Program finished."
        )


# =========================================================
# 程序入口
# =========================================================

if __name__ == "__main__":

    main()