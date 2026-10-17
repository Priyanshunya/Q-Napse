#!/usr/bin/env python3
"""
Q-Napse Stage 1: 802.11 Information-Element (IE) MAC De-Randomization Engine
Collapses 150+ randomized iOS/Android probe requests into True Unique Survivor Counts.
"""
import argparse
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler


class IEMacDeRandomizer:
    def __init__(self, eps: float = 0.85, min_samples: int = 2):
        self.eps = eps
        self.min_samples = min_samples
        self.scaler = StandardScaler()

    @staticmethod
    def extract_24d_ie_vector(probe_pkt: dict) -> np.ndarray:
        vec = np.zeros(24, dtype=np.float32)
        vec[0] = float(probe_pkt.get("ie_order_crc", 0) % 1024)
        vec[1] = float(probe_pkt.get("ht_capabilities", 0))
        vec[2] = float(probe_pkt.get("vht_capabilities", 0))
        vec[3] = float(probe_pkt.get("he_mcs_set", 0))
        vec[4] = float(probe_pkt.get("vendor_oui_hash", 0) % 512)
        vec[5] = float(probe_pkt.get("seq_delta_mod4096", 1))
        vec[6] = float(probe_pkt.get("burst_dt_ms", 25.0))
        vec[7:24] = np.array(probe_pkt.get("ie_length_profile", [0] * 17)[:17], dtype=np.float32)
        return vec

    def estimate_true_survivor_count(self, probe_bursts: list[dict]) -> dict:
        if not probe_bursts:
            return {"naive_mac_count": 0, "true_survivor_count": 0, "reduction_ratio": 0.0}

        unique_random_macs = len({p["src_mac"] for p in probe_bursts})
        feature_matrix = np.vstack([self.extract_24d_ie_vector(p) for p in probe_bursts])
        X_scaled = self.scaler.fit_transform(feature_matrix)

        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples, metric="euclidean").fit(X_scaled)
        labels = clustering.labels_
        true_survivors = len(set(labels) - {-1})

        return {
            "naive_mac_count": unique_random_macs,
            "true_survivor_count": true_survivors,
            "phantom_macs_rejected": unique_random_macs - true_survivors,
            "cluster_labels": labels.tolist(),
        }


def run_self_test():
    rng = np.random.default_rng(42)
    synthetic_probes = []
    base_profiles = [
        {"ie_order_crc": 311, "ht_capabilities": 0x19AD, "vht_capabilities": 0x0380, "he_mcs_set": 0xFFFA, "vendor_oui_hash": 102},
        {"ie_order_crc": 742, "ht_capabilities": 0x01EF, "vht_capabilities": 0x0000, "he_mcs_set": 0x0000, "vendor_oui_hash": 299},
        {"ie_order_crc": 518, "ht_capabilities": 0x11CE, "vht_capabilities": 0x0390, "he_mcs_set": 0xFFFC, "vendor_oui_hash": 410},
        {"ie_order_crc": 889, "ht_capabilities": 0x19AD, "vht_capabilities": 0x0120, "he_mcs_set": 0xFFF0, "vendor_oui_hash": 19},
    ]
    for idx in range(60):
        profile = base_profiles[idx % 4].copy()
        profile["src_mac"] = f"da:a1:19:{idx:02x}:{rng.integers(10, 99):02x}:fe"
        profile["seq_delta_mod4096"] = 1 + rng.normal(0, 0.05)
        profile["burst_dt_ms"] = (20.0 * ((idx % 4) + 1)) + rng.normal(0, 0.2)
        profile["ie_length_profile"] = [(idx % 4) * 5 + 10] * 17
        synthetic_probes.append(profile)

    engine = IEMacDeRandomizer()
    res = engine.estimate_true_survivor_count(synthetic_probes)
    print(f"[Q-Napse IE-DBSCAN] Naive MACs Seen: {res['naive_mac_count']} -> True Survivors: {res['true_survivor_count']}")
    assert res["true_survivor_count"] == 4, "Expected exactly 4 de-randomized survivor clusters!"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        run_self_test()
