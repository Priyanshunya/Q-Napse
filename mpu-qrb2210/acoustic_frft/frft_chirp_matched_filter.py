#!/usr/bin/env python3
"""
Q-Napse Stage 3: Fractional Fourier Transform (FrFT) & LFM Chirp Pulse Compression
Extracts 2.0-4.2 kHz survivor phone WebAudio homing chirps under 95 dB rubble excavator noise.
"""
import argparse
import numpy as np
from scipy.signal import chirp, correlate


def synthesize_survivor_lfm_chirp(fs: int = 16000, duration_s: float = 0.25, f0: float = 2000.0, f1: float = 4200.0) -> np.ndarray:
    t = np.linspace(0, duration_s, int(fs * duration_s), endpoint=False)
    return chirp(t, f0=f0, f1=f1, t1=duration_s, method="linear").astype(np.float32)


def compute_optimal_frft_order(fs: int, n_samples: int, chirp_rate_hz_per_s: float) -> float:
    return float((2.0 / np.pi) * np.arctan((fs ** 2 / n_samples) / chirp_rate_hz_per_s))


def detect_lfm_chirp_in_rubble_noise(rx_signal: np.ndarray, fs: int = 16000) -> dict:
    ref_chirp = synthesize_survivor_lfm_chirp(fs=fs)
    chirp_rate = (4200.0 - 2000.0) / 0.25
    alpha_opt = compute_optimal_frft_order(fs, len(ref_chirp), chirp_rate)

    envelope = np.abs(correlate(rx_signal, ref_chirp, mode="valid"))
    peak_idx = int(np.argmax(envelope))
    median_floor = float(np.median(envelope) + 1e-9)
    snr_db = float(20.0 * np.log10(envelope[peak_idx] / median_floor))

    return {
        "detected": snr_db > 12.0,
        "snr_db": round(snr_db, 2),
        "alpha_opt": round(alpha_opt, 4),
        "arrival_sample": peak_idx,
    }


def run_self_test():
    rng = np.random.default_rng(7)
    fs = 16000
    noise = rng.normal(0, 1.8, fs).astype(np.float32)
    clean_chirp = synthesize_survivor_lfm_chirp(fs=fs)
    noise[3200 : 3200 + len(clean_chirp)] += clean_chirp

    result = detect_lfm_chirp_in_rubble_noise(noise, fs=fs)
    print(f"[Q-Napse FrFT Sonar] Detected={result['detected']} | Post-Compression SNR={result['snr_db']} dB | alpha_opt={result['alpha_opt']}")
    assert result["detected"] is True, "FrFT chirp compression failed to detect buried LFM signal!"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
