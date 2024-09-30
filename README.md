# Readme

这是NIS3302信息安全科技创新的课程项目：基于编码器-解码器的入侵检测系统的代码。

## Introduction

系统采用基于图神经网络 (graph neural network) 的新型编码器-解码器架构，大致分为四个功能模块：

- Graph Construction and Representation: 对各种格式的系统日志进行解析，提取出每条日志的起始结点以及事件类型、时间戳信息，并将其表示为时序图的形式，输出一个带有时间信息的有向图。
- Graph Learning: 根据上一步输出的有向图，基于一定的规则，训练一对编码器和解码器，使其能够充分学习到正常日志的特征。
- Anomaly Detection: 输入带有时间信息的日志有向图，根据模型的计算结果，为每条日志标记误差，再基于一定的规则，判断出每个时间窗口的异常指数，当大于一定阈值时，触发告警。
- Anomaly Visualization: 在触发告警后，系统会迅速定位，并提取可疑成分，生成一张可视化的攻击逻辑图，便于做进一步的分析。



## Usage

### 环境依赖

具体的版本依赖要求见requirements.txt，直接运行以下命令

```bash
pip install -r requirements.txt
```

### 程序运行

按照Makefile里程序的顺序运行即可，注意在运行之前参看config.py文件中的配置，建立相应的文件夹。

由于提交的文件大小限制，我们将原始数据以及中间数据文件都去除了。原始数据可以在[google drive](https://drive.google.com/drive/folders/1QlbUFWAGq3Hpl8wVdzOdIoZLFxkII4EK)上下载

