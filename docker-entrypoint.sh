#!/bin/sh
# Say out loud whether anything the learner makes will survive this container.
#
# xrpl-camp writes a wallet, a certificate and a proof pack into the working
# directory, and the whole point of the product is that the learner keeps them.
# Run without a volume and the container exits having produced nothing — which
# looks identical to a successful run right up until the terminal closes.
#
# A warning is the honest option here rather than a refusal: `--help`,
# `--version` and `try` are genuinely useful without a mount, and a container
# that refuses to start is a worse workshop experience than one that tells you
# what it is about to do.

set -eu

WORK=/work

is_mounted() {
    # A bind/named volume puts /work on a different device from /. Compare the
    # two rather than looking for a mount table, which is not always readable
    # inside the container.
    root_dev=$(stat -c %d / 2>/dev/null || echo 0)
    work_dev=$(stat -c %d "$WORK" 2>/dev/null || echo 0)
    [ "$root_dev" != "$work_dev" ]
}

if ! is_mounted; then
    # stderr, not stdout. This is a warning about the environment, not output of
    # the command being run. On stdout it corrupted `docker run ... --version`
    # in our own release check -- a small preview of what it would do to anyone
    # piping this container's output.
    printf '\033[33m' >&2
    cat >&2 <<'WARNING'
  /work is not mounted.

  Everything xrpl-camp creates -- your wallet, your certificate, your proof
  pack -- is written to /work, and without a volume it is deleted when this
  container exits. The lessons will run and the transactions will be real,
  but you will walk away with nothing to keep.

  Stop and re-run with a volume if you want to keep the record:

      docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start

WARNING
    printf '\033[0m' >&2
fi

exec xrpl-camp "$@"
