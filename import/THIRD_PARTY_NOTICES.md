# Third-Party Notices

This project uses third-party open-source packages installed through `requirements.txt`.

Before publishing binary releases, review the exact installed package versions and their license files from the Python environment used to build the release.

Current core dependency notes from the local environment:

| Package | Local Version | License Metadata |
| --- | ---: | --- |
| PyInstaller | 6.20.0 | GPLv2-or-later with bootloader exception / Apache-2.0 components |
| faster-whisper | 1.2.1 | MIT |
| SoundCard | 0.4.6 | BSD 3-Clause |
| requests | 2.33.1 | Apache-2.0 |
| pystray | 0.19.5 | LGPLv3 |
| Pillow | 12.2.0 | See installed package metadata |
| cryptography | 48.0.0 | See installed package metadata |
| numpy | 2.4.4 | See installed package metadata |

Notes:

- PyInstaller's bootloader exception is intended to allow distributing apps built with PyInstaller.
- `pystray` is LGPLv3, so binary distribution should preserve license notices and allow users to replace/inspect the library as required by the license.
- Model files downloaded from Hugging Face or Ollama may have their own licenses. Review the selected model license before redistributing model weights.
