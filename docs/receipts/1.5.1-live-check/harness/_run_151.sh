set -u
cd ~ && rm -rf camp-151-linux camp-150-asset && git clone -q https://github.com/mcp-tool-shop-org/xrpl-camp camp-151-linux && cd camp-151-linux && git checkout -q 854c31f556866d76144a9bad98cb368141543846 && git log --oneline -1 && grep -m1 '^version' pyproject.toml
out=<scratch>/1.5.1-854c31f/linux
mkdir -p "$out" ~/camp-150-asset && cd ~/camp-150-asset
curl -fsSL -o xrpl-camp-1.5.0-linux-x64 https://github.com/mcp-tool-shop-org/xrpl-camp/releases/download/v1.5.0/xrpl-camp-1.5.0-linux-x64
curl -fsSL -o checksums-1.5.0.txt https://github.com/mcp-tool-shop-org/xrpl-camp/releases/download/v1.5.0/checksums-1.5.0.txt
{ sha256sum xrpl-camp-1.5.0-linux-x64; grep linux-x64 checksums-1.5.0.txt; } > "$out/neg-control-150-sha256.txt"
cat "$out/neg-control-150-sha256.txt"
bash <scratch>/_harness/linux_build_151.sh ~/camp-151-linux "$out" ~/camp-150-asset/xrpl-camp-1.5.0-linux-x64
cp ~/camp-150-asset/xrpl-camp-1.5.0-linux-x64 "$out/"
echo DONE
