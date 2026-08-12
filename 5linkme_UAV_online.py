# -*- coding:utf-8 -*-

import ctypes
import serial
import threading
import numpy as np
import time
from djitellopy import Tello


from scipy.signal import (
    butter,
    filtfilt,
    resample_poly
)


import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation



# =========================
# 配置
# =========================

DLL_PATH = r"E:\matlab_script\BCIhat\念及\BCI_UAV\LinkMe.dll"

PORT = "COM11"

BAUDRATE = 460800
# =========================
# UAV配置
# =========================

TELLO_IP = "10.110.204.199"

UAV_SPEED = 30

MAX_COMMAND = 10


drone = None

is_flying = False

command_count = 0

# 设备采样率

FS_DEVICE = 1000


# CCA采样率

FS_CCA = 250



CHANNELS = 8



# CCA窗口

WINDOW_TIME = 2

WINDOW_SIZE = (
    FS_CCA *
    WINDOW_TIME
)



# SSVEP频率

SSVEP_FREQS = [

    6,
    7.5,
    8.57,
    10,
    12

]


SSVEP_LABELS = [

    "前进",
    "后退",
    "左移",
    "右移",
    "起飞"

]


# 谐波数量

HARMONICS = 3




# =========================
# 加载DLL
# =========================


linkme = ctypes.CDLL(
    DLL_PATH
)


linkme.dataProtocol.argtypes = (

    ctypes.POINTER(
        ctypes.c_ubyte
    ),

    ctypes.c_int

)


linkme.dataProtocol.restype = ctypes.c_int



linkme.getData.restype = ctypes.POINTER(

    ctypes.POINTER(
        ctypes.c_double
    )

)





# =========================
# 数据缓存
# =========================


buffer = bytearray()


lock = threading.Lock()


running=True




# =========================
# CCA缓存
# =========================


cca_buffer=np.empty(

    (
        0,
        CHANNELS
    )

)





# =========================
# 滤波
# =========================


def bandpass_filter(
        data,
        low,
        high,
        fs
):


    b,a=butter(

        4,

        [
            low/(fs/2),
            high/(fs/2)
        ],

        btype='band'

    )


    return filtfilt(

        b,
        a,
        data,
        axis=0

    )

# =========================
# UAV控制函数
# =========================

def execute_uav_command(command):

    global is_flying
    global command_count


    # 起飞
    if command == "起飞":

        if not is_flying:

            print("UAV takeoff")

            drone.takeoff()

            is_flying = True

            time.sleep(2)

        return



    # 未起飞不执行移动

    if not is_flying:
        return



    # 达到10次动作

    if command_count >= MAX_COMMAND:

        print("动作次数达到10次，降落")

        drone.land()

        is_flying=False

        return



    print(
        "执行无人机:",
        command
    )


    if command=="前进":

        drone.send_rc_control(
            0,
            UAV_SPEED,
            0,
            0
        )


    elif command=="后退":

        drone.send_rc_control(
            0,
            -UAV_SPEED,
            0,
            0
        )


    elif command=="左移":

        drone.send_rc_control(
            -UAV_SPEED,
            0,
            0,
            0
        )


    elif command=="右移":

        drone.send_rc_control(
            UAV_SPEED,
            0,
            0,
            0
        )

    else:

        return



    # 保持1秒

    time.sleep(1.5)



    # 停止

    drone.send_rc_control(
        0,
        0,
        0,
        0
    )


    command_count += 1


    print(
        "完成动作:",
        command_count,
        "/",
        MAX_COMMAND
    )



    # 10次自动降落

    if command_count >= MAX_COMMAND:

        print(
            "执行次数达到限制，自动降落"
        )


        time.sleep(1)


        drone.land()

        is_flying=False



# =========================
# DLL解析
# =========================


def decode(data):


    buf=(

        ctypes.c_ubyte *
        len(data)

    )(*data)



    size=linkme.dataProtocol(

        buf,

        len(data)

    )


    if size<=0:

        return None



    ptr=linkme.getData()



    eeg=np.zeros(

        (
            size,
            9
        )

    )



    for i in range(size):

        for j in range(9):

            eeg[i,j]=ptr[i][j]



    return eeg





# =========================
# 降采样
# =========================


def downsample_eeg(data):


    """

    1000Hz
    ↓
    250Hz


    """


    return resample_poly(

        data,

        1,

        4,

        axis=0

    )






# =========================
# CCA参考信号
# =========================


def generate_reference(

        freq,
        length,
        fs,
        harmonics=3

):


    t=np.arange(length)/fs


    ref=[]



    for h in range(
        1,
        harmonics+1
    ):


        ref.append(

            np.sin(

                2*np.pi*h*freq*t

            )

        )


        ref.append(

            np.cos(

                2*np.pi*h*freq*t

            )

        )



    return np.array(ref).T






# =========================
# CCA计算
# =========================


def cca_corr(
        X,
        Y
):


    X=X-np.mean(
        X,
        axis=0
    )


    Y=Y-np.mean(
        Y,
        axis=0
    )



    C=np.cov(

        np.hstack(
            (
                X,
                Y
            )
        ).T

    )



    n=X.shape[1]

    Cxx=C[:n,:n]

    Cyy=C[n:,n:]

    Cxy=C[:n,n:]



    ex,Ux=np.linalg.eigh(Cxx)

    ey,Uy=np.linalg.eigh(Cyy)



    Wx=Ux @ np.diag(

        1/
        np.sqrt(
            ex+1e-8
        )

    ) @ Ux.T



    Wy=Uy @ np.diag(

        1/
        np.sqrt(
            ey+1e-8
        )

    ) @ Uy.T




    M=Wx@Cxy@Wy



    r=np.linalg.svd(
        M,
        compute_uv=False
    )[0]


    return r





# =========================
# SSVEP分类
# =========================


def ssvep_classify(
        eeg
):


    scores=[]



    for freq in SSVEP_FREQS:


        ref=generate_reference(

            freq,

            len(eeg),

            FS_CCA,

            HARMONICS

        )



        score=cca_corr(

            eeg,

            ref

        )


        scores.append(score)



    index=np.argmax(
        scores
    )



    return (

        SSVEP_LABELS[index],

        SSVEP_FREQS[index],

        scores

    )


# =========================
# 显示缓存
# =========================

DISPLAY_TIME = 5

display_buffer = np.zeros(
    (
        FS_DEVICE * DISPLAY_TIME,
        CHANNELS
    )
)


# =========================
# CCA原始数据缓存
# =========================
#
# 这里保存1000Hz原始EEG
#
# 每累计2000点
# ↓
# 取出2秒
# ↓
# 1000Hz → 250Hz
# ↓
# 得到500 × 8数据
# ↓
# 5-30Hz滤波
# ↓
# CCA
#

cca_raw_buffer = np.empty(
    (
        0,
        CHANNELS
    )
)


# =========================
# 最近一次分类结果
# =========================

last_result = "等待数据"

last_frequency = 0

last_scores = []


# =========================
# 串口接收线程
# =========================

def serial_receive(ser):

    global buffer

    while running:

        try:

            data = ser.read(
                25 * 136
            )

            if len(data):

                with lock:

                    buffer.extend(data)

        except Exception as e:

            print(
                "串口接收错误:",
                e
            )

            break


# =========================
# matplotlib初始化
# =========================

fig, ax = plt.subplots(
    figsize=(12, 8)
)


lines = []


x = np.arange(
    FS_DEVICE * DISPLAY_TIME
) / FS_DEVICE


for ch in range(CHANNELS):

    line, = ax.plot(
        x,
        display_buffer[:, ch],
        linewidth=1
    )

    lines.append(line)


ax.set_xlim(
    0,
    DISPLAY_TIME
)


ax.set_ylim(
    -100,
    CHANNELS * 100
)


ax.set_xlabel(
    "Time(s)"
)


ax.set_ylabel(
    "EEG(uV)"
)


ax.set_title(
    "LinkMe EEG 5-20Hz Filter"
)


ax.grid(True)





# =========================
# 实时更新
# =========================

def update(frame):

    global display_buffer

    global cca_raw_buffer

    global last_result

    global last_frequency

    global last_scores


    data = None


    # =========================
    # 取数据包
    # =========================

    with lock:

        if len(buffer) >= 25 * 136:

            data = buffer[
                :25 * 136
            ]

            del buffer[
                :25 * 136
            ]


    if data is not None:

        # =========================
        # DLL解析
        # =========================

        eeg = decode(data)


        if eeg is None:

            return lines


        # =========================
        # 前8通道
        # =========================

        eeg = eeg[:, :CHANNELS]


        # =========================
        # 显示滤波
        #
        # 保持原来的1000Hz
        # 5-20Hz
        # =========================

        try:

            eeg_display = bandpass_filter(
                eeg,
                5,
                20,
                FS_DEVICE
            )

        except Exception:

            return lines


        # =========================
        # 更新显示缓存
        # =========================

        n = len(
            eeg_display
        )


        if n < len(display_buffer):

            display_buffer[:-n] = (
                display_buffer[n:]
            )

            display_buffer[-n:] = (
                eeg_display
            )

        else:

            display_buffer[:] = (
                eeg_display[
                    -len(display_buffer):
                ]
            )


        # =========================
        # CCA原始数据缓存
        #
        # 注意：
        # 这里不直接对小数据包降采样
        #
        # 先累计1000Hz数据
        # =========================

        cca_raw_buffer = np.vstack(
            (
                cca_raw_buffer,
                eeg
            )
        )


        # =========================
        # 检查是否达到2秒
        #
        # 1000Hz × 2s = 2000点
        # =========================

        while len(
            cca_raw_buffer
        ) >= FS_DEVICE * WINDOW_TIME:


            # =========================
            # 取出严格2秒数据
            # =========================

            segment_raw = cca_raw_buffer[
                :FS_DEVICE * WINDOW_TIME
            ]


            # 剩余数据继续留在缓存
            cca_raw_buffer = cca_raw_buffer[
                FS_DEVICE * WINDOW_TIME:
            ]


            print()
            print(
                "========================================"
            )

            print(
                "开始SSVEP分类"
            )

            print(
                "原始数据:",
                segment_raw.shape,
                "1000Hz"
            )


            # =========================
            # 1000Hz → 250Hz
            # =========================

            try:

                segment = downsample_eeg(
                    segment_raw
                )

            except Exception as e:

                print(
                    "降采样失败:",
                    e
                )

                continue


            # 防止resample_poly产生的长度
            # 与预期不一致

            if len(segment) > WINDOW_SIZE:

                segment = segment[
                    :WINDOW_SIZE
                ]

            elif len(segment) < WINDOW_SIZE:

                print(
                    "降采样后数据长度异常:",
                    len(segment)
                )

                continue


            print(
                "降采样后:",
                segment.shape,
                "250Hz"
            )


            # =========================
            # 5-30Hz滤波
            # =========================

            try:

                segment_filter = bandpass_filter(
                    segment,
                    5,
                    30,
                    FS_CCA
                )

            except Exception as e:

                print(
                    "CCA滤波失败:",
                    e
                )

                continue


            # =========================
            # CCA分类
            # =========================

            try:

                (
                    result,
                    frequency,
                    scores
                ) = ssvep_classify(
                    segment_filter
                )

            except Exception as e:

                print(
                    "CCA计算失败:",
                    e
                )

                continue


            # =========================
            # 保存分类结果
            # =========================

            last_result = result

            last_frequency = frequency

            last_scores = scores


            # =========================
            # 输出分类结果
            # =========================

            print()
            print(
                "========== CCA分类结果 =========="
            )


            print(
                "识别结果:",
                result
            )
            execute_uav_command(result)

            print(
                "识别频率:",
                frequency,
                "Hz"
            )


            print(
                "--------------------------------"
            )


            for i in range(
                len(SSVEP_FREQS)
            ):

                print(
                    "{:<6} Hz  {:<4}  CCA = {:.4f}".format(
                        SSVEP_FREQS[i],
                        SSVEP_LABELS[i],
                        scores[i]
                    )
                )


            print(
                "================================"
            )


            # =========================
            # 目前暂时不接无人机
            # 后续可以在这里接控制指令
            # =========================

            #
            # if result == "前进":
            #     drone.forward()
            #
            # elif result == "后退":
            #     drone.back()
            #
            # elif result == "左移":
            #     drone.left()
            #
            # elif result == "右移":
            #     drone.right()
            #
            # elif result == "起飞":
            #     drone.takeoff()
            #


        # =========================
        # 更新EEG显示波形
        # =========================

        for ch in range(CHANNELS):

            lines[ch].set_ydata(
                display_buffer[:, ch]
            )


        # =========================
        # 更新SSVEP分类结果
        # =========================

       
    return lines


# =========================
# 主程序
# =========================

if __name__ == "__main__":

    ser = None

    try:
        # =========================
        # 初始化无人机
        # =========================




        drone = Tello(
            host=TELLO_IP
        )


        drone.connect()


        print(
            "UAV battery:",
            drone.get_battery()
        )

        # =========================
        # 自动起飞
        # =========================

        print("UAV takeoff")

        drone.takeoff()

        is_flying = True

        time.sleep(3)
        # =========================
        # 打开串口
        # =========================

        ser = serial.Serial(
            PORT,
            BAUDRATE,
            timeout=1
        )


        print(
            "----------------------------------------"
        )

        print(
            "LinkMe EEG启动"
        )

        print(
            "串口:",
            PORT
        )

        print(
            "设备采样率:",
            FS_DEVICE,
            "Hz"
        )

        print(
            "CCA采样率:",
            FS_CCA,
            "Hz"
        )

        print(
            "显示通道:",
            CHANNELS
        )

        print(
            "显示滤波: 5-20Hz"
        )

        print(
            "CCA滤波: 5-30Hz"
        )

        print(
            "CCA窗口:",
            WINDOW_TIME,
            "秒"
        )

        print(
            "CCA数据:",
            WINDOW_SIZE,
            "点 ×",
            CHANNELS,
            "通道"
        )

        print(
            "----------------------------------------"
        )

        print(
            "SSVEP目标:"
        )

        for i in range(
            len(SSVEP_FREQS)
        ):

            print(
                "  {:.2f} Hz -> {}".format(
                    SSVEP_FREQS[i],
                    SSVEP_LABELS[i]
                )
            )

        print(
            "----------------------------------------"
        )


        # =========================
        # 启动串口线程
        # =========================

        t = threading.Thread(
            target=serial_receive,
            args=(ser,),
            daemon=True
        )


        t.start()


        # =========================
        # 启动实时显示
        # =========================

        ani = FuncAnimation(
            fig,
            update,
            interval=50,
            blit=True,
            cache_frame_data=False
        )


        plt.show()


    except KeyboardInterrupt:

        print()
        print(
            "用户停止程序"
        )


    except Exception as e:

        print(
            "程序运行错误:",
            e
        )


    finally:

        # =========================
        # 停止线程
        # =========================

        running = False

        if drone is not None:

            try:

                drone.send_rc_control(
                    0,
                    0,
                    0,
                    0
                )


                if is_flying:

                    drone.land()


                drone.end()


            except Exception:

                pass

        # =========================
        # 关闭串口
        # =========================

        if ser is not None:

            try:

                ser.close()

            except Exception:

                pass


        print(
            "停止采集"
        )