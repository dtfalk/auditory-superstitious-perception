import numpy as np
import sounddevice as sd
import time

FS = 8000
DTYPE = "int16"
CH = 1

def hostapi_name(i):
    return sd.query_hostapis()[i]["name"]

def list_wdmks_outputs():
    devs = sd.query_devices()
    out = []
    for i, d in enumerate(devs):
        if d["max_output_channels"] <= 0:
            continue
        hname = hostapi_name(d["hostapi"])
        if "WDM-KS" in hname:
            out.append((i, d["name"], hname))
    return out

def try_play(idx, blocksize, latency):
    t = np.arange(FS) / FS
    tone = 0.2 * np.sin(2*np.pi*440*t)
    pcm = (tone * 32767).astype(np.int16).reshape(-1, 1)

    with sd.OutputStream(
        device=idx,
        samplerate=FS,
        channels=CH,
        dtype=DTYPE,
        blocksize=blocksize,
        latency=latency,
    ) as s:
        s.write(pcm)

def main():
    wdm = list_wdmks_outputs()
    print("WDM-KS outputs:")
    for i, name, hname in wdm:
        print(f"  {i}: {name} | {hname}")

    for i, name, _ in wdm:
        print(f"\nTrying {i}: {name}")
        try:
            try_play(i, blocksize = 256, latency = "low")
            print("  OK at 8000 Hz")
            return
        except Exception as e:
            print("  FAIL:", e)
            time.sleep(0.05)

    print("\nNo WDM-KS device accepted 8000 Hz.")

if __name__ == "__main__":
    main()
