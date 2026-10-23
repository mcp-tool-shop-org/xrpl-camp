set -u
out=<scratch>/npm-152-release-20261023T0740Z/linux
bash <scratch>/_harness/npm_release_check.sh ~/opt/node-v22.22.3-linux-x64/bin "$out" 1.5.2
# check_bundle.py (from the v1.5.2 tag) on the release linux asset, downloaded on its own and on the launcher's copy
rm -rf ~/camp-152-tag ~/camp-152-asset && git clone -q https://github.com/mcp-tool-shop-org/xrpl-camp ~/camp-152-tag && cd ~/camp-152-tag && git checkout -q v1.5.2 && git rev-parse HEAD > "$out/08-tag-head.txt"
uv venv -q -p 3.12 .venv && uv pip install -q "pyinstaller>=6.9.0,<7.0" > /dev/null 2>&1
mkdir -p ~/camp-152-asset && curl -fsSL -o ~/camp-152-asset/xrpl-camp-1.5.2-linux-x64 https://github.com/mcp-tool-shop-org/xrpl-camp/releases/download/v1.5.2/xrpl-camp-1.5.2-linux-x64
(cd ~/camp-152-asset && sha256sum xrpl-camp-1.5.2-linux-x64) > "$out/08-release-asset-sha256.txt"
for pair in "09-check-bundle-release-asset:$HOME/camp-152-asset/xrpl-camp-1.5.2-linux-x64" "10-check-bundle-launcher-cache:$out/xdg-cache/mcptoolshop/xrpl-camp/1.5.2/xrpl-camp-1.5.2-linux-x64"; do
  n=${pair%%:*}; b=${pair#*:}
  { echo "+ check_bundle.py --list <$n>"; .venv/bin/python scripts/check_bundle.py --list "$b"; } > "$out/$n.log" 2>&1; echo $? > "$out/$n.exit"
done
cp ~/camp-152-asset/xrpl-camp-1.5.2-linux-x64 "$out/"
echo DONE
