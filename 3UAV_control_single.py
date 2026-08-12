# UAV single dance
from djitellopy import Tello
import time


# =========================
# 参数设置
# =========================
TELLO_IP = "10.60.51.199"

# 环绕半径，单位 cm
# 以前方 100 cm 的点作为圆心，绕一圈
ORBIT_RADIUS = 100

# 曲线飞行速度，单位 cm/s
ORBIT_SPEED = 30

AFTER_FLIP_SLEEP = 3


def hover(drone, seconds=1.0):
    """悬停"""
    drone.send_rc_control(0, 0, 0, 0)
    time.sleep(seconds)


def spin_in_place_360(drone):
    """
    原地旋转 360°。
    这个比 send_rc_control 计时旋转精确得多。
    """
    print("开始原地旋转 360°...")
    drone.rotate_clockwise(360)
    hover(drone, 1)
    print("原地旋转完成")


def orbit_front_point_360(drone, radius=100, speed=30):
    """
    以前方 radius cm 的点为圆心，近似环绕 360°。

    坐标理解：
    当前无人机位置为 (0, 0)
    前方圆心为 (radius, 0)
    绕这个圆心飞一圈，半径为 radius

    用两段 curve 拼成一圈：
    第一段：从当前位置绕到圆心前方对侧
    第二段：从对侧绕回当前位置
    """
    print(f"开始以前方 {radius} cm 处为圆心环绕 360°...")

    r = radius

    try:
        # 第一段半圆：
        # 起点：当前位置 (0, 0)
        # 中间点：(r, r)
        # 终点：(2r, 0)
        drone.curve_xyz_speed(
            r, r, 0,
            2 * r, 0, 0,
            speed
        )
        time.sleep(1)

        # 第二段半圆：
        # 当前点相当于全局 (2r, 0)
        # 中间点相对当前位置为 (-r, -r)
        # 终点相对当前位置为 (-2r, 0)，即回到原点
        drone.curve_xyz_speed(
            -r, -r, 0,
            -2 * r, 0, 0,
            speed
        )
        time.sleep(1)

        hover(drone, 1)
        print("前方圆心环绕完成")

    except Exception as e:
        print("环绕执行失败:", e)
        hover(drone, 1)


def main():
    drone = Tello(host=TELLO_IP)

    try:
        print("连接无人机...")
        drone.connect()

        battery = drone.get_battery()
        print("Battery:", battery)

        if battery < 50:
            print("电量低于 50%，不建议执行翻滚和环绕动作。")
            return

        print("起飞...")
        drone.takeoff()
        time.sleep(3)

        # 为翻滚和环绕留安全高度
        print("上升至安全高度...")
        drone.move_up(50)
        time.sleep(2)

        # 1. 原地旋转 360°
        spin_in_place_360(drone)

        # 2. 左翻滚
        print("左翻滚...")
        drone.flip_left()
        time.sleep(AFTER_FLIP_SLEEP)

        # 3. 右翻滚
        print("右翻滚...")
        drone.flip_right()
        time.sleep(AFTER_FLIP_SLEEP)

        # 4. 以前方为圆心环绕 360°
        orbit_front_point_360(
            drone,
            radius=ORBIT_RADIUS,
            speed=ORBIT_SPEED
        )

        # 5. 降落
        print("准备降落...")
        hover(drone, 1)
        drone.land()
        print("降落完成")

    except KeyboardInterrupt:
        print("手动中断，准备降落...")
        try:
            hover(drone, 0.5)
            drone.land()
        except Exception as e:
            print("land error:", e)

    except Exception as e:
        print("执行异常:", e)
        print("尝试降落...")
        try:
            hover(drone, 0.5)
            drone.land()
        except Exception as land_error:
            print("land error:", land_error)

    finally:
        try:
            drone.end()
        except Exception:
            pass


if __name__ == "__main__":
    main()