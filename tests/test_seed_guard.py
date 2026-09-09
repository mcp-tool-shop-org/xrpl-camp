"""The seed-leak guard, as a control rather than as decoration.

`certificate_has_seed` and `proof_pack_has_seed` used to be exercised by six
assertions across two modules while being called from nowhere in
`xrpl_camp/` — a tested-but-uncalled security check, which reads as coverage
on a scorecard and stops nothing. They are now wired into `save_certificate`
and `save_proof_pack` fail-closed, so what has to be tested is the REFUSAL to
write, not the predicate in isolation.

The other half of a detector's contract is its false-positive rate. The old
tests only ever fed it synthetic two-key dicts; these feed it real generated
seeds of both key families, and real prose containing the substring "sed".
"""

from __future__ import annotations

import pytest
from xrpl.wallet import Wallet

from xrpl_camp.certificate import (
    SeedLeakDetected,
    certificate_has_seed,
    generate_certificate,
    save_certificate,
)
from xrpl_camp.models import Session
from xrpl_camp.proof_pack import (
    generate_proof_pack,
    proof_pack_has_seed,
    save_proof_pack,
)


def _session() -> Session:
    s = Session(started_at="2026-01-01T00:00:00Z", wallet_address="rCampAddress")
    s.mark_complete(1, "Mental Model")
    s.mark_complete(2, "Create Wallet")
    s.mark_complete(4, "Send Payment", txid="DEADBEEF1234")
    return s


# ---------------------------------------------------------------------------
# The guard actually refuses the write
# ---------------------------------------------------------------------------


def test_save_certificate_refuses_to_write_a_leaked_seed(tmp_path):
    """Fail closed. The file must not exist afterwards."""
    cert = generate_certificate(_session())
    cert["note"] = Wallet.create().seed
    target = tmp_path / "cert.json"

    with pytest.raises(SeedLeakDetected) as exc:
        save_certificate(cert, str(target))

    assert not target.exists(), "the certificate was written despite the guard"
    assert exc.value.error.code == "SEED_LEAK_DETECTED"
    assert exc.value.exit_code != 0


def test_save_proof_pack_refuses_to_write_a_leaked_seed(tmp_path):
    pack = generate_proof_pack(_session())
    pack["note"] = Wallet.create().seed
    target = tmp_path / "pack.json"

    with pytest.raises(SeedLeakDetected):
        save_proof_pack(pack, str(target))

    assert not target.exists()


def test_a_seed_hidden_inside_prose_is_still_refused(tmp_path):
    """Tokenised scanning, not an exact-value match."""
    cert = generate_certificate(_session())
    cert["note"] = f"remember: {Wallet.create().seed} (do not lose this)"
    target = tmp_path / "cert.json"

    with pytest.raises(SeedLeakDetected):
        save_certificate(cert, str(target))

    assert not target.exists()


def test_a_seed_nested_in_a_list_is_still_refused(tmp_path):
    cert = generate_certificate(_session())
    cert["completed"] = [*cert["completed"], {"note": Wallet.create().seed}]
    target = tmp_path / "cert.json"

    with pytest.raises(SeedLeakDetected):
        save_certificate(cert, str(target))

    assert not target.exists()


# ---------------------------------------------------------------------------
# Both key families, from real generated wallets
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("algorithm", ["ed25519", "secp256k1"])
def test_a_real_seed_of_either_family_is_detected(algorithm):
    """secp256k1 seeds have no fixed prefix.

    A detector built only on the "sEd" marker mislabels every secp256k1 seed as
    safe, so the ones it would wave through are exactly the ones a prefix test
    cannot see. This one decodes with xrpl-py's own base58 codec.
    """
    from xrpl.constants import CryptoAlgorithm

    seed = Wallet.create(algorithm=CryptoAlgorithm(algorithm)).seed
    if algorithm == "secp256k1":
        assert not seed.startswith("sEd"), (
            "a secp256k1 seed must not carry the ed25519 marker, or this test "
            "is not exercising the base58 path"
        )

    assert certificate_has_seed({"note": seed})
    assert proof_pack_has_seed({"note": seed})


def test_the_address_is_not_mistaken_for_a_seed():
    """The certificate's whole purpose is to carry the public address."""
    address = Wallet.create().address

    assert not certificate_has_seed({"address": address})
    assert not proof_pack_has_seed({"address": address})


# ---------------------------------------------------------------------------
# False positives — prose must survive
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "sed the file into shape",
        "Used seed money to fund the project",
        "Lesson 2: Create Wallet",
        "The seed stays on this machine",
        "supersede the previous certificate",
        "rCampAddress",
        "2026-01-01T00:00:00Z",
    ],
)
def test_ordinary_prose_does_not_trip_the_guard(text):
    """A guard that fires on the word "seed" would refuse a real certificate.

    Lesson 2's own copy says "Seed saved to .xrpl-camp/wallet.json"; the naive
    `"seed" in text.lower()` check the old tests implied would have refused to
    write any certificate that quoted it.
    """
    assert not certificate_has_seed({"note": text})
    assert not proof_pack_has_seed({"note": text})


def test_a_clean_certificate_still_writes(tmp_path):
    """The guard must not be a wall."""
    cert = generate_certificate(_session())
    target = tmp_path / "cert.json"

    written = save_certificate(cert, str(target))

    assert written.exists()
    assert not certificate_has_seed(cert)


def test_a_clean_proof_pack_still_writes(tmp_path):
    pack = generate_proof_pack(_session())
    target = tmp_path / "pack.json"

    written = save_proof_pack(pack, str(target))

    assert written.exists()
    assert not proof_pack_has_seed(pack)
