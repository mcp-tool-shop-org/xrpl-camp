# XRPL Camp — for workshops where installing things is the hard part.
#
# The product's promise is that you walk away with something: a wallet, a
# transaction on a public ledger, and a proof pack you keep. A container is
# the fastest way to get thirty people to a working terminal, and also the
# easiest way to throw all of that away — everything xrpl-camp writes lives in
# the working directory, and an unmounted container discards it on exit.
#
# So this image is built to be run with a volume, and it says so out loud when
# it is not (see docker-entrypoint.sh). It does not silently succeed at
# producing nothing.
#
#   docker run --rm -it -v "$PWD:/work" ghcr.io/mcp-tool-shop-org/xrpl-camp start
#
# Testnet only, like every other way of running this. No real money is
# reachable from inside here.

FROM python:3.13-slim

# OCI metadata so the package page on ghcr says what this is.
LABEL org.opencontainers.image.title="XRPL Camp"
LABEL org.opencontainers.image.description="Learn the XRP Ledger in one sitting — real transactions, portable proof, 10 minutes."
LABEL org.opencontainers.image.source="https://github.com/mcp-tool-shop-org/xrpl-camp"
LABEL org.opencontainers.image.url="https://mcp-tool-shop-org.github.io/xrpl-camp/"
LABEL org.opencontainers.image.licenses="MIT"

# Rich draws box-drawing characters and check marks. A container whose stdout
# encoding is ASCII turns lesson 1 into a UnicodeEncodeError, which is exactly
# the failure the health pass fixed on Windows consoles.
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY xrpl_camp/ ./xrpl_camp/

RUN pip install --no-cache-dir . \
    && find /usr/local -name '__pycache__' -type d -prune -exec rm -rf {} + \
    && rm -rf /src

# A learner's seed should not be written by root, and a workshop laptop should
# not end up with root-owned files in the folder they mounted.
RUN useradd --create-home --uid 1000 camper
USER camper

# Everything the tool writes -- .xrpl-camp/, the certificate, the proof pack --
# lands here. Mount it or lose it; the entrypoint says which is happening.
#
# Deliberately NOT `VOLUME ["/work"]`. That declaration makes Docker create an
# ANONYMOUS volume when the caller supplies none, which is discarded by --rm
# and near-impossible to find without it -- so the learner loses their proof
# pack either way, and /work always sits on a different device, which silently
# defeated the entrypoint's mount check. A warning that cannot fire is worse
# than no warning: it reads like a guarantee. Without VOLUME, an unmounted
# /work is ordinary container filesystem, the check works, and the caller is
# told the truth.
WORKDIR /work

COPY --chmod=0755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["start"]
