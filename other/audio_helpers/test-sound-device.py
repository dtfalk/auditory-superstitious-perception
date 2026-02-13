import numpy as np
import sounddevice as sd
import time

TARGET_DTYPE = "int16"
CHANNELS = 1

def hostapi_name(hostapi_index: int) -> str:
    return sd.query_hostapis()[hostapi_index]["name"]

def list_motu_outputs_verbose():
    devs = sd.query_devices()
    out = []
    for i, d in enumerate(devs):
        if d["max_output_channels"] <= 0:
            continue
        if "motu" not in d["name"].lower():
            continue
        out.append((i, d["name"], d["hostapi"], hostapi_name(d["hostapi"])))
    return out

def try_open_and_play(device_index, fs):
    # 0.25 sec 440 Hz tone
    t = np.arange(int(fs * 0.25)) / fs
    tone = 0.2 * np.sin(2 * np.pi * 440 * t)
    pcm16 = (tone * 32767).astype(np.int16).reshape(-1, 1)

    extra = sd.WasapiSettings(exclusive=True)

    with sd.OutputStream(
        device=device_index,
        samplerate=fs,
        channels=CHANNELS,
        dtype=TARGET_DTYPE,
        extra_settings=extra,
        blocksize=0,
        latency="low",
    ) as stream:
        stream.write(pcm16)
        stream.write(np.zeros((int(fs * 0.02), 1), dtype=np.int16))

def main():
    print("Host APIs:")
    for i, api in enumerate(sd.query_hostapis()):
        print(f"  {i}: {api['name']}")

    motu = list_motu_outputs_verbose()
    if not motu:
        print("No MOTU output devices found.")
        return

    print("\nMOTU outputs (with host API):")
    for idx, name, hapi, hname in motu:
        print(f"  {idx:>3}: {name}  | hostapi={hapi} ({hname})")

    wasapi_motu = [(idx, name) for idx, name, _, hname in motu if "WASAPI" in hname]
    print("\nWASAPI MOTU outputs:")
    for idx, name in wasapi_motu:
        print(f"  {idx:>3}: {name}")

    if not wasapi_motu:
        print("\nNo WASAPI MOTU devices detected. Something is odd with your PortAudio build.")
        return

    # Try 8k first, then common device-native rates
    rates_to_try = [8000, 11025, 16000, 22050, 32000, 44100, 48000, 96000]

    failures = []
    for idx, name in wasapi_motu:
        print(f"\nTrying device {idx}: {name}")
        for fs in rates_to_try:
            try:
                print(f"  - rate {fs} ... ", end="", flush=True)
                try_open_and_play(idx, fs)
                print("OK")
                print(f"\nSUCCESS: device={idx} rate={fs}")
                return
            except Exception as e:
                print(f"FAIL ({e})")
                failures.append((idx, name, fs, repr(e)))
                time.sleep(0.05)

    print("\nNo WASAPI-exclusive configuration worked.")
    print("Sample failures:")
    for idx, name, fs, err in failures[:12]:
        print(f"  dev {idx} ({name}) @ {fs}: {err}")

if __name__ == "__main__":
    main()
