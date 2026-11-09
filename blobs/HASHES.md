# Blob hashes (SHA-256)

Machine-readable copy: [manifest.json](manifest.json). Installers refuse a file whose
on-device hash is neither the stock nor the patched value (gralloc excepted: it is a full
stock replacement).

| Device path | Stock (MIUI 14.0.4.0 SJSEUXM) | Shipped |
|---|---|---|
| `/system/lib64/libcamera_algoup_jni.xiaomi.so` | `d8a3b6b93a83a82e2be5fb5f4f864ce64a7a213a49b7ba52f607d6ba82bfdcaa` | `3dda8c37bc34ab57b6b56067c7ab142c83dc31c0372153e8fe25cbb0e9cca384` |
| `/system/lib64/libcamera_mianode_jni.xiaomi.so` | `1feb745b06770c6b38a301bb3b37fd90ba3785a092beb5eaf1f5fec3b3a8cb9a` | `1f89d499fbf9304142ee65be2a3fe5f1d4572210356b2773f43a60e551a30b74` |
| `/vendor/lib64/libcamera_dirty.so` | `e9bbad41ca6f8a27ea4b01f9c53e849e8ad323e6c718506cf38e673e04b01959` | `cb4d11cddcf23556950bb30a206d7f657b6b2b2a62f68fc8a5cba017a5e5e0bc` |
| `/vendor/lib64/camera/components/com.vidhance.node.eis.so` | `2a9d6395292681bd73b20f84348cf2a17435ac4caa925c26dea719123be29b49` | `a3dc87d9575bd120512225b67b0c4756c8fd2fa98ee998d085f171881d1af47f` |
| `/vendor/lib64/hw/gralloc.lito.so` | (any) | `596323b879026275e1852a371c378920f7636b1c07f725fe1516dcef92f0cf5a` (stock MIUI 14) |
| `/vendor/lib/hw/gralloc.lito.so` | (any) | `a0720637cab2483e79b67a94271e16188228e1b6910d6f95318e89d8345b7954` (stock MIUI 14) |

Intermediate Vidhance node with only the NV21 patch:
`3652e3553dd9ff03543575d9491cf4128d05d91b916bed9a8861f409cf1687f9`.
