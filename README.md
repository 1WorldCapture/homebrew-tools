# homebrew-tools

`homebrew-tools` 是一个用于发布 macOS 工具的 Homebrew tap。

当前仓库主要提供一个 Formula：[`funasr-onnx`](./Formula/funasr-onnx.rb)，用于**通过源码构建并分发** [FunASR](https://github.com/1WorldCapture/FunASR) 的 `runtime/onnxruntime` 命令行工具。

## 安装

```bash
brew tap 1worldcapture/tools
brew install funasr-onnx
```

也可以直接使用 tap 全名安装：

```bash
brew install 1worldcapture/tools/funasr-onnx
```

## 当前提供的 Formula

### `funasr-onnx`

`funasr-onnx` 会从源码构建 FunASR 的 ONNX Runtime CLI 工具。

- 上游仓库：[`1WorldCapture/FunASR`](https://github.com/1WorldCapture/FunASR)
- 发布标签：`ll-0.1`
- 构建目录：`runtime/onnxruntime`
- 构建方式：CMake
- 平台范围：**macOS**

### 安装后包含的命令

#### ASR / VAD / Punctuation / RTF

- `funasr-onnx-offline`
- `funasr-onnx-offline-vad`
- `funasr-onnx-online-vad`
- `funasr-onnx-online-asr`
- `funasr-onnx-offline-punc`
- `funasr-onnx-online-punc`
- `funasr-onnx-offline-rtf`
- `funasr-onnx-online-rtf`

#### 2-pass

- `funasr-onnx-2pass`
- `funasr-onnx-2pass-rtf`

#### 模型下载辅助命令

- `funasr-download-models`

这个命令来自上游的 `runtime/onnxruntime/scripts/download_models.sh`，安装后以更适合作为 CLI 的名字暴露出来。

## 使用说明

### 1. 查看各命令帮助

```bash
funasr-onnx-offline --help
funasr-onnx-online-asr --help
funasr-onnx-2pass --help
```

### 2. 下载模型

Homebrew **不会自动安装模型文件**。请根据你的场景单独准备模型目录。

可以先查看下载脚本帮助：

```bash
funasr-download-models --help
```

下载完成后，再把对应的模型目录传给相应的 CLI 命令。

## 说明与限制

- 当前 Formula 面向 **macOS**。
- 安装过程为**源码构建**，不是预编译二进制分发。
- 模型文件**不随 Formula 一起安装**。
- 当前 macOS 构建**不包含 ITN**。
- 在 macOS 下，建议按上游当前实现将其视为面向 **WAV / PCM 风格输入** 的命令行工具集合。

## 仓库结构

```text
homebrew-tools/
├── Formula/
│   └── funasr-onnx.rb
└── README.md
```

## 自动跟进上游版本

仓库内提供了自动检查上游 FunASR `ll-x.y` 标签的流程：

- GitHub Actions：`.github/workflows/funasr-upstream-sync.yml`
- 同步脚本：`scripts/sync_funasr_release.py`

默认行为：

- 定时检查上游 `1WorldCapture/FunASR` 的最新 `ll-x.y` tag
- 发现新 tag 后，自动更新：
  - `Formula/funasr-onnx.rb` 的 `url` / `version` / `sha256`
  - README 中记录的发布标签
- 自动推送一个分支并创建 / 更新 PR

也可以手动触发 workflow，并指定某个 tag 重新同步；默认不会回退到更旧的 tag，除非显式允许降级。

> 注意：如果上游“移动已有 tag”而不是创建新 tag，这套流程会刷新当前 tag 的 `sha256` 并发起 PR，但更稳妥的做法仍然是发布新的不可变 tag。

## 维护说明

如果需要手动发布新的 FunASR 版本，通常可以直接运行同步脚本，或手动更新以下内容：

1. `Formula/funasr-onnx.rb` 中的：
   - `url`
   - `version`
   - `sha256`
2. README 中提到的上游 tag 或说明文字
3. 本地验证命令：

```bash
python3 scripts/sync_funasr_release.py --dry-run
brew install --build-from-source 1worldcapture/tools/funasr-onnx
brew test funasr-onnx
```

## 相关链接

- 本仓库：[`1WorldCapture/homebrew-tools`](https://github.com/1WorldCapture/homebrew-tools)
- 上游源码：[`1WorldCapture/FunASR`](https://github.com/1WorldCapture/FunASR)
- Homebrew 文档：<https://docs.brew.sh/>
