class FunasrOnnx < Formula
  desc "FunASR ONNX Runtime command-line tools for macOS"
  homepage "https://github.com/1WorldCapture/FunASR"
  url "https://github.com/1WorldCapture/FunASR/archive/refs/tags/ll-0.1.tar.gz"
  version "0.1"
  sha256 "64696112eff23194cdb459b9a1d25c4bf21a21f7617c4cc7979fee6febd7eb28"
  license "MIT"

  resource "json" do
    url "https://github.com/nlohmann/json/archive/refs/tags/v3.11.2.tar.gz"
    sha256 "d69f9deb6a75e2580465c6c4c5111b89c4dc2fa94e3a85fcd2ffcd9a143d9273"
  end

  depends_on "cmake" => :build
  depends_on "ffmpeg"
  depends_on "gflags"
  depends_on "onnxruntime"

  def install
    odie "funasr-onnx currently supports macOS only" unless OS.mac?

    runtime_dir = buildpath/"runtime/onnxruntime"
    build_dir = runtime_dir/"build"
    private_lib_dir = libexec/"lib"
    json_dir = runtime_dir/"third_party/json"
    rm_r json_dir if json_dir.exist?
    json_dir.mkpath

    resource("json").stage do
      json_dir.install Dir["*"]
    end

    inreplace runtime_dir/"third_party/yaml-cpp/CMakeLists.txt",
              "cmake_policy(SET CMP0012 OLD)",
              "cmake_policy(SET CMP0012 NEW)"
    inreplace runtime_dir/"third_party/yaml-cpp/CMakeLists.txt",
              "cmake_policy(SET CMP0015 OLD)",
              "cmake_policy(SET CMP0015 NEW)"

    targets = %w[
      funasr-onnx-offline
      funasr-onnx-offline-vad
      funasr-onnx-online-vad
      funasr-onnx-online-asr
      funasr-onnx-offline-punc
      funasr-onnx-online-punc
      funasr-onnx-offline-rtf
      funasr-onnx-online-rtf
    ]

    system "cmake", "-S", runtime_dir, "-B", build_dir, *std_cmake_args,
                    "-DCMAKE_BUILD_TYPE=Release",
                    "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
                    "-DGPU=OFF",
                    "-DENABLE_GLOG=ON",
                    "-DENABLE_FST=ON",
                    "-DONNXRUNTIME_DIR=#{Formula["onnxruntime"].opt_prefix}",
                    "-DFFMPEG_DIR=#{Formula["ffmpeg"].opt_prefix}"

    system "cmake", "--build", build_dir, "--parallel", "--target", *targets

    bin.install targets.map { |target| build_dir/"bin"/target }
    private_lib_dir.install build_dir/"src/libfunasr.dylib"

    private_lib_dir.install build_dir/"third_party/yaml-cpp/libyaml-cpp.0.6.0.dylib"
    private_lib_dir.install_symlink "libyaml-cpp.0.6.0.dylib" => "libyaml-cpp.0.6.dylib"
    private_lib_dir.install_symlink "libyaml-cpp.0.6.dylib" => "libyaml-cpp.dylib"

    private_lib_dir.install build_dir/"third_party/openfst/src/lib/libfst.16.dylib"
    private_lib_dir.install_symlink "libfst.16.dylib" => "libfst.dylib"

    private_lib_dir.install build_dir/"third_party/glog/libglog.0.7.0.dylib"
    private_lib_dir.install_symlink "libglog.0.7.0.dylib" => "libglog.1.dylib"
    private_lib_dir.install_symlink "libglog.1.dylib" => "libglog.dylib"

    pkgshare.install runtime_dir/"scripts/download_models.sh"

    installed_bins = targets.map { |target| bin/target }
    installed_libs = private_lib_dir.children.select { |path| path.file? && !path.symlink? }

    installed_bins.each do |file|
      add_rpath_if_missing(file, "@loader_path/../libexec/lib")
      delete_build_rpaths(file, build_dir)
    end

    installed_libs.each do |file|
      add_rpath_if_missing(file, "@loader_path")
      delete_build_rpaths(file, build_dir)
    end
  end

  def caveats
    <<~EOS
      FunASR models are not installed by Homebrew.
      Download them separately and pass the model directories at runtime.

      A helper download script is installed at:
        #{opt_pkgshare}/download_models.sh

      macOS builds currently exclude ITN support.
      On macOS, treat this formula as supporting WAV/PCM-style inputs only.
    EOS
  end

  test do
    assert_match "USAGE:", shell_output("#{bin}/funasr-onnx-offline --help")
    assert_match "USAGE:", shell_output("#{bin}/funasr-onnx-online-asr --help")
    assert_match "USAGE:", shell_output("#{bin}/funasr-onnx-offline-punc --help")
  end

  private

  def add_rpath_if_missing(file, rpath)
    return if current_rpaths(file).include?(rpath)

    system "install_name_tool", "-add_rpath", rpath, file
  end

  def delete_build_rpaths(file, build_dir)
    current_rpaths(file).each do |rpath|
      next unless rpath.start_with?(build_dir.to_s, buildpath.to_s)

      system "install_name_tool", "-delete_rpath", rpath, file
    end
  end

  def current_rpaths(file)
    output = Utils.safe_popen_read("otool", "-l", file)
    lines = output.lines

    lines.each_with_index.filter_map do |line, index|
      next unless line.include?("cmd LC_RPATH")

      path_line = lines[(index + 1)..].find { |candidate| candidate.include?("path ") }
      next unless path_line

      path_line.split("path ").last.split(" (offset").first.strip
    end
  end
end
