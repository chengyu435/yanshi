# 5linkme_UAV_online.py 分析

## 代码整体功能

这个脚本是一个基于 EEG/SSVEP 的无人机实时控制程序，主要作用是：

- 从 `LinkMe.dll` 读取 EEG 数据
- 通过串口从 EEG 设备获取原始数据
- 对 EEG 信号做滤波、降采样、CCA 分类
- 将识别到的频率对应到指令（前进、后退、左移、右移、起飞）
- 用 `djitellopy` 控制 Tello 无人机执行动作
- 用 `matplotlib` 实时显示 EEG 波形

---

## 关键模块

### 1. 配置部分

- `DLL_PATH`：外部 DLL 路径
- `PORT`, `BAUDRATE`：串口参数
- `TELLO_IP`：无人机 IP 地址
- `UAV_SPEED`, `MAX_COMMAND`：移动速度与最大动作次数
- `FS_DEVICE = 1000`：设备采样率
- `FS_CCA = 250`：CCA 使用的采样率
- `CHANNELS = 8`：使用前 8 通道 EEG
- `WINDOW_TIME = 2`：CCA 窗口 2 秒
- `SSVEP_FREQS` 与 `SSVEP_LABELS`：5 个频点与对应指令

### 2. DLL 接口

- `linkme.dataProtocol(buf, len)`：解析原始字节流，返回数据点数
- `linkme.getData()`：获取 EEG 数据指针

### 3. 数据解码

函数 `decode(data)`：

- 将 `bytes` 转成 `c_ubyte` 数组
- 调用 DLL 解析
- 从返回的指针读出 EEG 数据到 `numpy` 数组
- 返回形状为 `(size, 9)` 的 EEG 数据

---

## 信号处理与分类

### 滤波

函数 `bandpass_filter(data, low, high, fs)`：

- 使用 4 阶 Butterworth 滤波器
- `filtfilt` 双向过滤，减少相位失真

### 降采样

函数 `downsample_eeg(data)`：

- 用 `resample_poly` 将 1000Hz 数据降到 250Hz

### 参考信号生成

函数 `generate_reference(freq, length, fs, harmonics=3)`：

- 生成频率 `freq` 的正弦、余弦参考信号
- 包含 1-3 次谐波

### CCA 计算

函数 `cca_corr(X, Y)`：

- 中心化 X、Y
- 计算协方差矩阵
- 对 X、Y 进行白化
- 计算 `Wx * Cxy * Wy`
- 取 SVD 的第一个奇异值作为相关性分数

### SSVEP 分类

函数 `ssvep_classify(eeg)`：

- 对每个目标频率生成参考信号
- 计算 CCA 相关分数
- 选最大分数对应的标签作为识别结果

---

## UAV 控制逻辑

函数 `execute_uav_command(command)`：

- 如果是 `"起飞"` 且无人机未起飞：执行 `drone.takeoff()`
- 如果无人机还未起飞，移动指令会被忽略
- 如果 `command_count >= MAX_COMMAND`：自动降落
- `前进/后退/左移/右移`：
  - 调用 `drone.send_rc_control(...)`
  - 维持 1.5 秒
  - 发送停止指令
  - `command_count += 1`
- 10 次动作后自动降落

---

## 实时循环

函数 `update(frame)` 是动画回调：

1. 从共享 `buffer` 中读取一个固定包长 `25 * 136`
2. 调用 `decode` 得到 EEG 数据
3. 取前 8 通道
4. 对显示数据做 5-20Hz 滤波并更新显示缓存
5. 将原始 1000Hz 数据累积到 `cca_raw_buffer`
6. 每当累积到 2000 点（2 秒）时：
   - 取出 2 秒数据
   - 降采样到 250Hz
   - 5-30Hz 滤波
   - 进行 SSVEP 分类
   - 调用 `execute_uav_command(result)`
   - 打印分类结果和各频率分数
7. 更新 `matplotlib` 中的曲线

---

## 主程序流程

在 `if __name__ == "__main__":`

- 初始化 `Tello` 无人机并连接
- 读取电池信息
- 直接自动起飞
- 打开串口，启动 `serial_receive` 线程
- 启动 `FuncAnimation` 实时绘图
- `plt.show()` 阻塞显示
- 程序结束或异常时：
  - 停止线程
  - 如果无人机在飞则降落
  - 断开无人机
  - 关闭串口

---

## 需要注意的点

- 程序默认先起飞再开始 EEG 控制
- `command_count` 达到 10 次后会自动降落，并且后续移动指令不会执行
- 包长度固定读取 `25*136`，这需要与设备数据格式匹配
- `bandpass_filter` 在文件中定义了两次，但后面一次覆盖前面一次，且两者相同
- 代码依赖 `LinkMe.dll`、`pyserial`、`djitellopy`、`scipy`、`matplotlib`

---

## 总结

这个程序实现了一个“EEG → SSVEP 频率分类 → Tello 控制”的闭环流程。它的核心是：

- 原始 EEG 数据读取
- 1000Hz → 250Hz 的降采样
- 5-30Hz 带通滤波
- 基于 CCA 的频率识别
- 将识别结果映射成无人机指令
