# VaultSeed Changelog

## 0.1.0 - Initial Release

### New
- Vault unlock/create flow with passphrase-based key derivation (PBKDF2-HMAC-SHA256, 100k iterations)
- AES-GCM encryption via KEF format using K210 hardware accelerators
- Encrypted manifest + individual encrypted secret files on microSD
- Automatic flash mirror backup (transparent, same ciphertext)
- Flash-to-SD restore when SD card is lost or corrupted
- Secret type auto-detection: BIP39 (12/24 words), Nostr nsec/npub, hex keys, text
- Add secrets via QR scan or manual text entry
- View secrets with 30-second auto-hide timeout
- Export secrets as QR codes
- Delete secrets with confirmation
- Passphrase strength indicator
- Maximum 5 unlock attempts before lockout

### Base
- Forked from Krux firmware (selfcustody/krux)
- Removed all Bitcoin transaction signing logic (wallet, PSBT, descriptors, key derivation)
- Retained: HAL, UI framework, QR engine, camera/display/SD drivers, KEF crypto engine
- Target hardware: Yahboom K210 (airgapped, no WiFi/BT)
