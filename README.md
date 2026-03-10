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

### Build on GitHub and flash Yahboom

If you want the simplest path without local Docker or WSL:

1. Open `Actions -> Build Yahboom Package` in GitHub
2. Click `Run workflow` on the branch you want to build
3. Download the artifact `vaultseed-yahboom-package`
4. Unzip it on Windows
5. Install the flashing dependency:

```powershell
py -3 -m pip install -r requirements-flash.txt
```

6. Flash the board, replacing `COM6` with the detected port:

```cmd
flash-yahboom.cmd COM6
```

The downloaded package already includes `kboot.kfpkg`, `firmware.bin`, `ktool.py`, and the helper scripts. If Windows does not show a COM port for the device, install the CH340/341 driver first.

The `Build` workflow was also simplified:

- On every `push`, it compiles only `maixpy_yahboom`
- From GitHub `Actions -> Build -> Run workflow`, you can still build `yahboom`, any other supported device, or `all`

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
