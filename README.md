# VaultSeed

VaultSeed is an airgapped firmware for Kendryte K210 devices (focused on Yahboom K210) to store and manage encrypted secrets offline.

It is designed as a practical secret vault for:
- BIP39 seed phrases
- Nostr private keys (`nsec`)
- Generic hex/text secrets

## Project status

This repository is the active development home for VaultSeed.

Current implementation includes:
- Vault unlock/create flow with passphrase-based key derivation
- Encrypted manifest + encrypted per-secret files
- SD primary storage with automatic flash mirror backup
- Secret management UI (add/view/reveal/QR/delete)

## Hardware target

Primary target:
- Yahboom K210

Also compatible with the current K210 board matrix already supported by the base firmware stack.

## Repository structure

- `src/boot.py`: firmware entrypoint (Vault flow)
- `src/krux/vault.py`: vault engine (encryption + storage)
- `src/krux/secret_types.py`: secret type detection
- `src/krux/pages/vault_pages/`: vault UI pages

## Development

### Clone

```bash
git clone https://github.com/VoidHashh/VaultSeed.git
cd VaultSeed
```

### Build firmware

Use the existing build helper script:

```bash
./krux build maixpy_yahboom
```

### Flash firmware

```bash
./krux flash maixpy_yahboom
```

### Python tooling

```bash
pip install poetry
poetry install
```

### Run tests

```bash
poetry run poe test
```

### Run simulator

```bash
poetry install --extras simulator
poetry run poe simulator-yahboom --sd
```

## Security notice

This project is under active development and has not been formally audited.
Use at your own risk.

## License

See [LICENSE.md](LICENSE.md).
