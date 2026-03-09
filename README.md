# homebrew-tools

Personal Homebrew tap for source-built macOS tools.

## Install

```bash
brew tap <owner>/tools
brew install funasr-onnx
```

## Formulae

### `funasr-onnx`

Builds the FunASR ONNX Runtime command-line tools from source using the `ll-0.1`
tag from [`1WorldCapture/FunASR`](https://github.com/1WorldCapture/FunASR).

Installed commands:

- `funasr-onnx-offline`
- `funasr-onnx-offline-vad`
- `funasr-onnx-online-vad`
- `funasr-onnx-online-asr`
- `funasr-onnx-offline-punc`
- `funasr-onnx-online-punc`
- `funasr-onnx-offline-rtf`
- `funasr-onnx-online-rtf`

Notes:

- Models are not installed by Homebrew.
- A helper model download script is installed into the formula's `pkgshare`.
- macOS builds exclude ITN support.
- The first release intentionally excludes the current 2-pass binaries.
