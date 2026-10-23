set -u
cd ~ && rm -rf camp-152 && git clone -q https://github.com/mcp-tool-shop-org/xrpl-camp camp-152 && cd camp-152 && git checkout -q 4a7ff84 && git log --oneline -1
out=<scratch>/1.5.2-4a7ff84/linux
mkdir -p "$out"
{ ls -ld /opt/uv-python; ls /opt/uv-python; test -w /opt/uv-python && echo "writable: yes"; } > "$out/00-uv-python-dir-before.txt" 2>&1
bash <scratch>/_harness/linux_build_152.sh ~/camp-152 "$out" ~/camp-150-asset/xrpl-camp-1.5.0-linux-x64
sha256sum ~/camp-150-asset/xrpl-camp-1.5.0-linux-x64 > "$out/neg-control-sha256.txt"
echo DONE
