set -u
cd ~ && rm -rf camp-151-g1 && git clone -q https://github.com/mcp-tool-shop-org/xrpl-camp camp-151-g1 && cd camp-151-g1 && git checkout -q 44dc45a && git log --oneline -1
out=<scratch>/1.5.1-g1-44dc45a/linux
mkdir -p "$out"
{ ls -la /opt/uv-python; test -w /opt/uv-python && echo "writable: yes"; } > "$out/00-uv-python-dir-before.txt" 2>&1
bash <scratch>/_harness/linux_build_151_g1.sh ~/camp-151-g1 "$out" ~/camp-150-asset/xrpl-camp-1.5.0-linux-x64
cd ~/camp-151-g1
{ echo "+ check_bundle.py <854c31f local binary>"; uv run --no-sync python scripts/check_bundle.py <scratch>/1.5.1-854c31f/linux/xrpl-camp-1.5.1-linux-x64; } > "$out/12-neg-control-854c31f-local.log" 2>&1; echo $? > "$out/12-neg-control-854c31f-local.exit"; echo "12: exit $(cat $out/12-neg-control-854c31f-local.exit)"
sha256sum ~/camp-150-asset/xrpl-camp-1.5.0-linux-x64 <scratch>/1.5.1-854c31f/linux/xrpl-camp-1.5.1-linux-x64 > "$out/neg-controls-sha256.txt"
echo DONE
