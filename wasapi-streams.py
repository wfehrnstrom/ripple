import pyaudiowpatch as pa

import time
import wave

p = pa.PyAudio()

DURATION = 5.0
CHUNK_SIZE = 512

devices = p.get_loopback_device_info_generator()

loopback_device_index = -1

for device in devices:
    for (k, v) in device.items():
        print(f"{k}: {v}")

    if device["name"] == "Speakers (Realtek(R) Audio) [Loopback]":
        loopback_device_index = device["index"]


speakers_realtek_audio_device = p.get_wasapi_loopback_analogue_by_index(loopback_device_index)

filename = "loopback_record.wav"

max_input_channels = speakers_realtek_audio_device["maxInputChannels"]
default_sample_rate = int(speakers_realtek_audio_device["defaultSampleRate"])

wave_file = wave.open(filename, 'wb')
wave_file.setnchannels(max_input_channels)
wave_file.setsampwidth(pa.get_sample_size(pa.paInt16))
wave_file.setframerate(default_sample_rate)

def callback(in_data, frame_count, time_info, status):
    wave_file.writeframes(in_data)
    return (in_data, pa.paContinue)

with p.open(format= pa.paInt16,
            channels=max_input_channels,
            rate=default_sample_rate,
            frames_per_buffer=CHUNK_SIZE,
            input=True,
            input_device_index=loopback_device_index,
            stream_callback=callback) as stream:
    """
        Open a PA stream via context manager.
        After leaving the context, everything will
        be correctly closed(Stream, PyAudio manager)            
    """
    print(f"The next {DURATION} seconds will be written to {filename}")
    time.sleep(DURATION) # Block execution while playing

wave_file.close()